/**
 * Task 5 🟡 — Permissions-aware retrieval.
 *
 * In a real knowledge base, not every document is visible to every user.
 * This task teaches you to attach per-document access metadata (owner, group,
 * visibility) during ingestion and to enforce it at retrieval time so a user
 * only sees chunks they are authorised to read.
 *
 * It also reinforces page/section-level citations: every chunk carries the
 * source document, section heading, and page number in its metadata so
 * answers can cite exactly where the information came from.
 *
 * What you'll learn:
 *   - Attaching an ACL (Access Control List) to chunks at ingestion time
 *   - Filtering BEFORE and AFTER vector search (pre-filter vs post-filter)
 *   - Why pre-filtering reduces result-set size and protects privacy
 *   - Carrying source + section + page metadata for precise citations
 *   - How vector databases expose metadata filters (e.g. Qdrant's `must` clauses)
 *
 * How to run:
 *   pnpm tsx modules/11-document-ingestion/ts/05-permissions-aware.ts
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ACL {
  owner: string;              // e.g. "alice"
  groups: string[];           // e.g. ["engineering", "all"]
  visibility: "private" | "group" | "public";
}

interface PermissionedChunk {
  id: string;
  text: string;
  vector: number[];
  // Citation metadata
  source: string;             // file path or URL
  section: string;            // heading text (e.g. "## Introduction")
  page: number;               // page number (0 if not applicable)
  // Access metadata
  acl: ACL;
}

interface RetrievalResult {
  chunk: PermissionedChunk;
  score: number;              // cosine similarity (higher = more relevant)
}

function citation(result: RetrievalResult): string {
  const parts: string[] = [`source=${JSON.stringify(result.chunk.source)}`];
  if (result.chunk.section) parts.push(`section=${JSON.stringify(result.chunk.section)}`);
  if (result.chunk.page > 0) parts.push(`page=${result.chunk.page}`);
  return parts.join(", ");
}

// ---------------------------------------------------------------------------
// Sample corpus with ACLs
// ---------------------------------------------------------------------------

interface RawDoc {
  text: string;
  source: string;
  section: string;
  page: number;
  acl: ACL;
}

const SAMPLE_DOCS: RawDoc[] = [
  {
    text: "The quarterly revenue report shows a 12% increase in Q3.",
    source: "finance/q3_report.pdf",
    section: "## Revenue Summary",
    page: 3,
    acl: { owner: "cfo", groups: ["finance", "exec"], visibility: "group" },
  },
  {
    text: "Employee handbook: all employees are entitled to 20 days of PTO.",
    source: "hr/handbook.md",
    section: "## Time Off Policy",
    page: 0,
    acl: { owner: "hr_team", groups: ["all"], visibility: "public" },
  },
  {
    text: "The production database password is stored in the secrets vault.",
    source: "ops/runbook.md",
    section: "## Credentials",
    page: 0,
    acl: { owner: "ops_lead", groups: ["sre", "devops"], visibility: "group" },
  },
  {
    text: "Our RAG pipeline uses section-aware chunking for better retrieval.",
    source: "eng/architecture.md",
    section: "## Document Ingestion",
    page: 0,
    acl: { owner: "alice", groups: ["engineering", "all"], visibility: "group" },
  },
  {
    text: "The CEO's personal compensation details are strictly confidential.",
    source: "exec/compensation.pdf",
    section: "## Executive Pay",
    page: 7,
    acl: { owner: "board", groups: ["board"], visibility: "private" },
  },
];

// Users and their group memberships
const USER_GROUPS: Record<string, string[]> = {
  alice: ["engineering", "all"],
  bob: ["finance", "exec", "all"],
  carol: ["sre", "devops", "all"],
  guest: ["all"],
};

// ---------------------------------------------------------------------------
// Step 1 — Tag access metadata during ingestion
// ---------------------------------------------------------------------------

/**
 * Create a PermissionedChunk by attaching ACL and citation metadata.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Return a PermissionedChunk with:
 *        id      = chunkId
 *        text    = doc.text
 *        vector  = vector
 *        source  = doc.source
 *        section = doc.section
 *        page    = doc.page ?? 0
 *        acl     = acl
 */
function tagAccess(doc: RawDoc, acl: ACL, chunkId: string, vector: number[]): PermissionedChunk {
  // TODO: implement tagAccess
  throw new Error("TODO: implement tagAccess()");
}

// ---------------------------------------------------------------------------
// Step 2 — Check whether a user may read a chunk
// ---------------------------------------------------------------------------

/**
 * Return true if `user` is allowed to read `chunk`.
 *
 * Access rules (in order):
 *   1. visibility === "public":  always allowed.
 *   2. visibility === "private": only the owner is allowed.
 *   3. visibility === "group":   allowed if the user is the owner or belongs
 *      to at least one of the ACL's groups.
 *
 * Use USER_GROUPS to look up the user's group memberships.
 * Unknown users have no groups.
 *
 * TODO: implement this function.
 */
function userCanAccess(user: string, chunk: PermissionedChunk): boolean {
  // TODO: implement userCanAccess
  throw new Error("TODO: implement userCanAccess()");
}

// ---------------------------------------------------------------------------
// Step 3 — Cosine similarity helper
// ---------------------------------------------------------------------------

/**
 * Compute cosine similarity between two equal-length vectors.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. dot = a.reduce((s, v, i) => s + v * b[i], 0)
 *   2. normA = Math.sqrt(a.reduce((s, v) => s + v * v, 0))
 *   3. normB = Math.sqrt(b.reduce((s, v) => s + v * v, 0))
 *   4. Guard: return 0 if normA === 0 || normB === 0.
 *   5. Return dot / (normA * normB).
 */
function cosineSimilarity(a: number[], b: number[]): number {
  // TODO: implement cosineSimilarity
  throw new Error("TODO: implement cosineSimilarity()");
}

// ---------------------------------------------------------------------------
// Step 4 — Retrieval with ACL enforcement
// ---------------------------------------------------------------------------

/**
 * Retrieve the top-k chunks relevant to `queryVector` that `user` may read.
 *
 * Supports two filtering modes (both must return the same results):
 *
 * PRE-FILTER (preFilter=true) — filter the candidate set BEFORE scoring:
 *   1. Filter index to chunks where userCanAccess(user, chunk) === true.
 *   2. Score filtered candidates with cosineSimilarity.
 *   3. Return top-k by score (highest first).
 *
 * POST-FILTER (preFilter=false) — score ALL chunks, then filter:
 *   1. Score every chunk with cosineSimilarity.
 *   2. Sort descending by score.
 *   3. Keep only results where userCanAccess(user, chunk) === true.
 *   4. Return first k of those.
 *
 * Pre-filtering is preferred in production: it is faster and avoids scoring
 * documents the user can never see. Post-filtering is shown here for comparison.
 *
 * TODO: implement both branches.
 *
 * Returns a list of RetrievalResult sorted by score (highest first).
 */
function retrieveForUser(
  queryVector: number[],
  user: string,
  index: PermissionedChunk[],
  k = 3,
  preFilter = true,
): RetrievalResult[] {
  // TODO: implement retrieveForUser
  throw new Error("TODO: implement retrieveForUser()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}  |  Embed model: ${provider.embedModel}\n`);

  // Embed all sample documents
  const texts = SAMPLE_DOCS.map((d) => d.text);
  console.log(`Embedding ${texts.length} sample documents...`);
  const embedResult = await provider.embed(texts);

  // Build the index
  const index: PermissionedChunk[] = SAMPLE_DOCS.map((doc, i) =>
    tagAccess(doc, doc.acl, `chunk_${i}`, embedResult.vectors[i]),
  );
  console.log(`Index built: ${index.length} chunks with ACLs attached.\n`);

  // Embed the query
  const query = "What is the company's time off policy?";
  console.log(`Query: "${query}"\n`);
  const queryVector = (await provider.embed([query])).vectors[0];

  // Retrieve for each user
  const users = ["alice", "bob", "carol", "guest"];
  for (const user of users) {
    const groups = USER_GROUPS[user] ?? [];
    console.log(`User: ${JSON.stringify(user)} (groups: [${groups.join(", ")}])`);

    const resultsPre = retrieveForUser(queryVector, user, index, 3, true);
    const resultsPost = retrieveForUser(queryVector, user, index, 3, false);

    const idsPre = resultsPre.map((r) => r.chunk.id).join(",");
    const idsPost = resultsPost.map((r) => r.chunk.id).join(",");
    if (idsPre !== idsPost) {
      console.warn("  WARNING: pre-filter and post-filter returned different results");
    }

    if (resultsPre.length > 0) {
      const top = resultsPre[0];
      console.log(`  Top result : ${JSON.stringify(top.chunk.text.slice(0, 70))}`);
      console.log(`  Citation   : ${citation(top)}`);
      console.log(`  Score      : ${top.score.toFixed(4)}`);
    } else {
      console.log("  No accessible results.");
    }
    console.log(
      `  Chunks returned: ${resultsPre.length} (pre-filter), ${resultsPost.length} (post-filter)\n`,
    );
  }

  // Access summary
  console.log("Access summary (guest vs bob):");
  for (const chunk of index) {
    const guestOk = userCanAccess("guest", chunk);
    const bobOk = userCanAccess("bob", chunk);
    console.log(`  ${chunk.source.padEnd(35)}  guest=${guestOk}  bob=${bobOk}`);
  }

  console.log(
    "\nKey insights:",
    "\n  1. ACL metadata is attached at ingestion time — not at query time.",
    "\n  2. Pre-filter avoids scoring documents the user cannot read (faster + safer).",
    "\n  3. Every result carries source + section + page for precise citations.",
    "\n  4. In production, vector DBs like Qdrant support metadata filters natively.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
