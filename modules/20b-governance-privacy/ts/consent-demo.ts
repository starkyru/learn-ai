/**
 * Consent + lawful-basis demo (Module 20b, Task 2).
 *
 * Walks one synthetic subject through: register activities -> capture consent ->
 * authorise several purposes -> withdraw consent -> re-authorise. It prints each
 * decision and structured-logs the audit trail, then shows consent GATING an
 * actual (fake) model call. Deterministic and offline.
 *
 * Run it:
 *   pnpm tsx modules/20b-governance-privacy/ts/consent-demo.ts
 *
 * Not legal advice — see the module README.
 */

import type { ChatMessage } from "@learn-ai/llm-core";
import { RecordingProvider } from "./fakes.js";
import {
  buildDefaultEngine,
  ConsentEngine,
  PURPOSE_ACCOUNT_SECURITY,
  PURPOSE_MARKETING_EMAIL,
  PURPOSE_ORDER_FULFILMENT,
  PURPOSE_PRODUCT_ANALYTICS,
} from "./consent.js";

const SUBJECT = "subj_0042"; // a pseudonymous subject id (never a raw identifier)
const ACTOR = "privacy-service";

function describe(engine: ConsentEngine, purpose: string): string {
  const decision = engine.canProcess(SUBJECT, purpose, { actor: ACTOR });
  const verb = decision.allowed ? "ALLOW" : "DENY ";
  const basis = decision.basis ?? "-";
  return `  ${verb} ${purpose.padEnd(18)} basis=${basis.padEnd(16)} ${decision.reason}`;
}

async function gatedMarketingDraft(engine: ConsentEngine): Promise<void> {
  const decision = engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL, {
    actor: ACTOR,
  });
  if (!decision.allowed) {
    console.log("\n[gated call] marketing draft SKIPPED — not authorised.");
    return;
  }
  const provider = new RecordingProvider();
  const messages: ChatMessage[] = [
    { role: "system", content: "You draft short, opt-in marketing emails." },
    { role: "user", content: `Draft a one-line note for subject ${SUBJECT}.` },
  ];
  const result = await provider.chat(messages, { temperature: 0, maxTokens: 64 });
  console.log(
    `\n[gated call] authorised by ${decision.basis}; model said: ${result.text}`,
  );
}

async function main(): Promise<void> {
  const engine = buildDefaultEngine({
    sink: (entry) => console.log(JSON.stringify(entry)),
  });

  engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
    actor: ACTOR,
    version: "2026.07.01",
  });
  engine.captureConsent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, {
    actor: ACTOR,
    version: "2026.07.01",
  });

  console.log("\nAfter capturing consent (marketing + account_security):");
  for (const purpose of [
    PURPOSE_MARKETING_EMAIL,
    PURPOSE_ORDER_FULFILMENT, // contract — no consent needed
    PURPOSE_PRODUCT_ANALYTICS, // consent-only, never granted -> deny
    PURPOSE_ACCOUNT_SECURITY, // allowed via consent (contract also present)
  ]) {
    console.log(describe(engine, purpose));
  }

  await gatedMarketingDraft(engine);

  engine.withdrawConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR });
  engine.withdrawConsent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, { actor: ACTOR });

  console.log("\nAfter withdrawing consent for both:");
  for (const purpose of [PURPOSE_MARKETING_EMAIL, PURPOSE_ACCOUNT_SECURITY]) {
    console.log(describe(engine, purpose));
  }
  console.log(
    "  ^ marketing is now DENIED (consent-only); account_security is STILL " +
      "ALLOWED under contract — withdrawal did not revoke the other basis.",
  );

  console.log(`\nAudit log holds ${engine.auditLog.length} records.`);
}

// Run only when invoked directly (tsx/node), never when imported.
const invokedPath = process.argv[1] ?? "";
if (
  invokedPath.endsWith("consent-demo.ts") ||
  invokedPath.endsWith("consent-demo.js")
) {
  void main();
}
