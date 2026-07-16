"use strict";
// Best-effort in-process network TRIPWIRE for the offline smoke runner (Node/TS
// child side) — NOT a sandbox. Loaded via NODE_OPTIONS=--require BEFORE the
// transpiled exercise runs. It trips a VIOLATION (sentinel on stderr) when an
// HONESTLY-MISCLASSIFIED offline exercise reaches out over the network: it wraps
// the common paths — TCP net.Socket#connect, UDP (dgram) connect/send, and DNS
// lookups — while allowing loopback / unix sockets.
//
// THREAT MODEL / LIMITATION: this catches honest mistakes, it is NOT a security
// boundary. Determined code can bypass it (native addons, a child process, other
// entry points). The DEFINITIVE guarantee is OS-level network isolation of the
// CI smoke job; this guard is defense-in-depth alongside the parent's
// secret-stripping and the static offline classifier.

const net = require("net");
const dns = require("dns");
const dgram = require("dgram");

const SENTINEL = "__SMOKE_NET_VIOLATION__";

// Loopback / unspecified only, computed from the address family (127.0.0.0/8,
// ::1, ::, 0.0.0.0) — not a literal allowlist. A hostname other than localhost
// is treated as outbound (resolving it is itself a leak).
function isLoopbackHost(host) {
  if (host == null) return true;
  if (typeof host !== "string") return false;
  if (host === "" || host === "localhost") return true;
  const kind = net.isIP(host);
  if (kind === 4) return host.startsWith("127.") || host === "0.0.0.0";
  if (kind === 6) return host === "::1" || host === "::";
  return false;
}

function violate(kind, host) {
  process.stderr.write(`${SENTINEL} ${kind} ${host}\n`);
  throw new Error(`SMOKE_NET_BLOCKED: outbound network denied to ${host} (${kind})`);
}

// --- TCP connect -----------------------------------------------------------
// Socket#connect is reached as connect(options[, cb]), connect(port[, host][,
// cb]), connect(path[, cb]), and — crucially — net.connect passes the
// PRE-NORMALIZED [options, cb] array as a single argument. Reduce all of them to
// a plain options object so host/path read reliably.
function optionsFromArgs(args) {
  let first = args[0];
  if (Array.isArray(first)) first = first[0];
  if (typeof first === "string") return { path: first };
  if (first && typeof first === "object") return first;
  return { port: first, host: typeof args[1] === "string" ? args[1] : undefined };
}

const realConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function connect(...args) {
  const opts = optionsFromArgs(args);
  if (typeof opts.path === "string" || isLoopbackHost(opts.host)) {
    return realConnect.apply(this, args);
  }
  violate("connect", opts.host);
};

// --- UDP (dgram) connect + send --------------------------------------------
const realDgramConnect = dgram.Socket.prototype.connect;
dgram.Socket.prototype.connect = function connect(port, ...rest) {
  const address = typeof rest[0] === "string" ? rest[0] : undefined;
  if (address === undefined || isLoopbackHost(address)) {
    return realDgramConnect.call(this, port, ...rest);
  }
  violate("dgram.connect", address);
};

const realSend = dgram.Socket.prototype.send;
dgram.Socket.prototype.send = function send(...args) {
  // send(msg, [offset, length,] port[, address][, cb]); address (a string) is
  // the destination host. No address => the connected peer, else loopback.
  let host;
  for (let i = 1; i < args.length; i += 1) {
    if (typeof args[i] === "string") {
      host = args[i];
      break;
    }
  }
  if (host === undefined) {
    try {
      host = this.remoteAddress().address; // connected peer, if any
    } catch {
      host = undefined; // not connected → real send will handle it
    }
  }
  if (host === undefined || isLoopbackHost(host)) {
    return realSend.apply(this, args);
  }
  violate("dgram.send", host);
};

// --- DNS -------------------------------------------------------------------
function guardDnsFn(obj, name) {
  const real = obj[name];
  if (typeof real !== "function") return;
  obj[name] = function guarded(hostname, ...rest) {
    if (isLoopbackHost(hostname)) return real.call(this, hostname, ...rest);
    violate(`dns.${name}`, hostname);
  };
}

const DNS_FNS = [
  "lookup",
  "lookupService",
  "resolve",
  "resolve4",
  "resolve6",
  "resolveAny",
  "resolveMx",
  "resolveTxt",
  "resolveCname",
  "resolveSrv",
  "resolvePtr",
  "reverse",
];
DNS_FNS.forEach((name) => guardDnsFn(dns, name));
if (dns.promises) {
  ["lookup", "resolve", "resolve4", "resolve6", "resolveAny", "reverse"].forEach(
    (name) => guardDnsFn(dns.promises, name),
  );
}
