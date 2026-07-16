"""Best-effort in-process network TRIPWIRE for smoke children (not a sandbox).

Installed inside each Python smoke child BEFORE the exercise runs. It patches the
COMMON socket + DNS entry points so an HONESTLY-MISCLASSIFIED offline exercise —
one that imports ``requests``/``httpx``/``socket`` and actually calls out — trips
a VIOLATION (``VIOLATION_SENTINEL`` on stderr) instead of silently reaching the
network. Loopback / AF_UNIX targets stay allowed, and it survives
``importlib.reload(socket)``.

THREAT MODEL / LIMITATION — this is a TRIPWIRE for honest mistakes, NOT a security
sandbox. Monkey-patching Python cannot enforce network denial against determined
or adversarial code: it does NOT block the low-level ``_socket`` module, direct
``ctypes``/libc syscalls, or a fresh reimport
(``del sys.modules['socket']; import socket``). Do not rely on it as a boundary.
The DEFINITIVE guarantee is OS-LEVEL network isolation of the CI smoke job (see
the CI workflow). This guard — together with the parent stripping provider
secrets and the static classifier keeping ``offline`` entries free of network
imports — is defense-in-depth that catches the common cases early and locally.
"""

from __future__ import annotations

import importlib
import ipaddress
import socket
import sys
from typing import IO

VIOLATION_SENTINEL = "__SMOKE_NET_VIOLATION__"

_LOOPBACK_NAMES = frozenset({"", "localhost"})

# Original callables, captured EXACTLY ONCE (before the first patch). A later
# importlib.reload(socket) rebinds socket's functions to fresh, unpatched
# versions; re-installing against these still-valid originals re-guards them
# without double-wrapping.
_ORIGINALS: dict[str, object] = {}


def _is_loopback_host(host: object) -> bool:
    """True for None / localhost / a loopback or unspecified IP; else False.

    A non-localhost hostname returns False: resolving it is itself an outbound
    leak, so it must be denied.
    """
    if host is None:
        return True
    if isinstance(host, bytes):
        try:
            host = host.decode()
        except UnicodeDecodeError:
            return False
    if not isinstance(host, str):
        return False
    if host in _LOOPBACK_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


def _address_host(address: object) -> object:
    """Host component of a socket address, or a unix-socket marker."""
    if isinstance(address, (str, bytes)):
        return "__unix__"
    if isinstance(address, (tuple, list)) and address:
        return address[0]
    return None


def _addr_allowed(family: int, address: object) -> bool:
    unix_family = getattr(socket, "AF_UNIX", None)
    if unix_family is not None and family == unix_family:
        return True
    host = _address_host(address)
    if host == "__unix__":
        return True
    return _is_loopback_host(host)


def install(stream: IO[str] | None = None) -> None:
    """Patch ``socket``/DNS so non-loopback outbound calls trip a violation.

    Idempotent and reload-safe: originals are captured once, and a hook re-applies
    the guard after ``importlib.reload(socket)``.
    """
    out: IO[str] = stream if stream is not None else sys.stderr

    if not _ORIGINALS:
        for name, obj in (
            ("connect", getattr(socket.socket, "connect", None)),
            ("connect_ex", getattr(socket.socket, "connect_ex", None)),
            ("send", getattr(socket.socket, "send", None)),
            ("sendto", getattr(socket.socket, "sendto", None)),
            ("sendmsg", getattr(socket.socket, "sendmsg", None)),
            ("create_connection", getattr(socket, "create_connection", None)),
            ("getaddrinfo", getattr(socket, "getaddrinfo", None)),
            ("gethostbyname", getattr(socket, "gethostbyname", None)),
            ("gethostbyname_ex", getattr(socket, "gethostbyname_ex", None)),
            ("gethostbyaddr", getattr(socket, "gethostbyaddr", None)),
            ("getnameinfo", getattr(socket, "getnameinfo", None)),
        ):
            _ORIGINALS[name] = obj

    def deny(kind: str, target: object) -> None:
        out.write(f"{VIOLATION_SENTINEL} {kind} {target!r}\n")
        out.flush()
        raise OSError("SMOKE_NET_BLOCKED: outbound network denied")

    def g_connect(self: socket.socket, address: object, *args: object) -> object:
        if _addr_allowed(self.family, address):
            return _ORIGINALS["connect"](self, address, *args)  # type: ignore[operator]
        deny("connect", address)
        return None

    def g_connect_ex(self: socket.socket, address: object, *args: object) -> object:
        if _addr_allowed(self.family, address):
            return _ORIGINALS["connect_ex"](self, address, *args)  # type: ignore[operator]
        deny("connect_ex", address)
        return None

    def g_send(self: socket.socket, *args: object, **kwargs: object) -> object:
        try:
            peer = self.getpeername()
        except OSError:
            peer = None
        if peer is not None and not _addr_allowed(self.family, peer):
            deny("send", peer)
        return _ORIGINALS["send"](self, *args, **kwargs)  # type: ignore[operator]

    def g_sendto(self: socket.socket, *args: object) -> object:
        address = args[-1] if args else None
        if _addr_allowed(self.family, address):
            return _ORIGINALS["sendto"](self, *args)  # type: ignore[operator]
        deny("sendto", address)
        return None

    def g_sendmsg(self: socket.socket, *args: object, **kwargs: object) -> object:
        address = args[3] if len(args) >= 4 else kwargs.get("address")
        if address is None or _addr_allowed(self.family, address):
            return _ORIGINALS["sendmsg"](self, *args, **kwargs)  # type: ignore[operator]
        deny("sendmsg", address)
        return None

    def g_create_connection(address: object, *args: object, **kwargs: object) -> object:
        host = address[0] if isinstance(address, (tuple, list)) and address else None
        if _is_loopback_host(host):
            return _ORIGINALS["create_connection"](address, *args, **kwargs)  # type: ignore[operator]
        deny("create_connection", address)
        return None

    def _host_guard(name: str, kind: str):
        def guard(host: object, *args: object, **kwargs: object) -> object:
            if _is_loopback_host(host):
                return _ORIGINALS[name](host, *args, **kwargs)  # type: ignore[operator]
            deny(kind, host)
            return None

        return guard

    def g_getnameinfo(sockaddr: object, *args: object, **kwargs: object) -> object:
        host = sockaddr[0] if isinstance(sockaddr, (tuple, list)) and sockaddr else None
        if _is_loopback_host(host):
            return _ORIGINALS["getnameinfo"](sockaddr, *args, **kwargs)  # type: ignore[operator]
        deny("getnameinfo", sockaddr)
        return None

    method_guards = {
        "connect": g_connect,
        "connect_ex": g_connect_ex,
        "send": g_send,
        "sendto": g_sendto,
        "sendmsg": g_sendmsg,
    }
    for name, guard in method_guards.items():
        if _ORIGINALS.get(name) is not None:
            setattr(socket.socket, name, guard)

    module_guards = {
        "create_connection": g_create_connection,
        "getaddrinfo": _host_guard("getaddrinfo", "getaddrinfo"),
        "gethostbyname": _host_guard("gethostbyname", "gethostbyname"),
        "gethostbyname_ex": _host_guard("gethostbyname_ex", "gethostbyname_ex"),
        "gethostbyaddr": _host_guard("gethostbyaddr", "gethostbyaddr"),
        "getnameinfo": g_getnameinfo,
    }
    for name, guard in module_guards.items():
        if _ORIGINALS.get(name) is not None:
            setattr(socket, name, guard)

    _install_reload_hook(out)


def _install_reload_hook(out: IO[str]) -> None:
    """Wrap ``importlib.reload`` so reloading ``socket`` re-applies the guard.

    This covers the honest ``importlib.reload(socket)`` case only; a determined
    ``del sys.modules['socket']; import socket`` fresh reimport is out of scope
    (that is what OS-level CI isolation is for).
    """
    current = importlib.reload
    if getattr(current, "_smoke_reguard", False):
        return

    def guarded_reload(module: object) -> object:
        result = current(module)  # type: ignore[arg-type]
        if getattr(module, "__name__", "") == "socket":
            install(out)
        return result

    guarded_reload._smoke_reguard = True  # type: ignore[attr-defined]
    importlib.reload = guarded_reload  # type: ignore[assignment]
