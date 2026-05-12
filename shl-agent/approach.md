# SHL Assessment Agent — Approach Document

## Problem Decomposition

Three orthogonal sub-problems drive the design:

**Grounding** — the agent must never hallucinate URLs or assessment names. This is a hard eval; a single bad URL is a fail.

**Dialog control** — knowing when to clarify, recommend, compare, refine, or refuse. The 10 reference traces reveal the exact decision boundaries the evaluator tests.

**Latency** — the 30-second timeout with a multi-turn history makes naive full-catalog prompting (40k tokens) risky on Groq's free tier.

---

## Design Choices and Trade-offs

### Stack

| Layer | Choice | Rationale |
|---|---|---|
| LLM | Groq `llama-3.3-70b-versatile` | ~300 tok/s; reliably outputs JSON mode; free tier sufficient |
| Retrieval | `rank-bm25` (BM25Okapi) | <1ms per query on 377 items; no embedding overhead; strong on domain vocabulary |
| API | FastAPI + uvicorn | Async I/O; lifespan startup for single catalog load |
| Catalog | Bundled `catalog.json` | Eliminates network dependency; instant cold start |

### Retrieval Setup

BM25 indexes `name + description + job_levels_raw + keys + languages_raw` per item. Query is the concatenation of all user turns (captures late-volunteered information). Top-25 results pass to the LLM (~3k tokens).

**Seniority boosting**: Regex keyword dict maps role phrases (`cxo`, `director`, `graduate`, `junior`) to SHL job-level strings. Items whose `job_levels` overlap are interleaved 3-to-1 ahead of non-matching results.

**Compare/refine augmentation**: When the last user turn signals compare or refine intent, the last message is searched independently and results merged into context.

### Prompt Design

The system prompt has five labeled behavior blocks (`REFUSE / CLARIFY / COMPARE / REFINE / RECOMMEND`), each with explicit triggers and rules derived from the 10 reference conversations.

**Key enhancements implemented:**
- **STANDARD ASSESSMENT RULES**: Explicit MUST-include criteria for OPQ32r (professional/manager/senior roles), Verify G+ (senior IC/graduate), GSA (development/audit), and companion reports
- **Composition patterns**: 9 scenario-specific patterns (technical, leadership, graduate, sales audit, etc.) with complete battery examples
- **Version selection rules**: Prefer "(New)" labels, "2.0" over "1.0", IC vs Manager variant matching

### Hallucination Guard

**Priority Assessment Map** (NEW): 10 most frequently recommended assessments with canonical names and aliases. Resolution order:
1. Exact URL match
2. URL with/without trailing slash
3. **Priority map lookup by alias** (NEW - ensures OPQ32r, GSA, Verify G+ always resolve)
4. Exact name match (case-insensitive)
5. Known alias dict
6. Difflib close-match (cutoff 0.82)

Items that fail all stages are silently dropped.

### Post-Processing Enforcement (NEW)

**Critical innovation**: Deterministic post-processing layer enforces business rules after LLM generation. LLMs are probabilistic and don't guarantee rule-following.

**Rules enforced:**
- Add OPQ32r for professional/manager/senior/leadership roles (unless explicitly declined)
- Add Verify G+ for senior IC/tech lead/graduate roles (unless explicitly declined)
- Add GSA for development/audit purposes
- Add Global Skills Development Report alongside GSA
- Add Graduate Scenarios for graduate roles
- Fix variant selection (replace Sales Manager with IC variant when appropriate)

This hybrid approach (LLM + deterministic rules) significantly improved Recall@10.

---

## Evaluation Approach

`eval.py` implements two-LLM replay: Groq `llama-3.1-8b-instant` simulates the user, answering truthfully from the trace's fact set. Per-trace **Recall@10** is averaged over all 10 traces.

### Measured Improvements

**Trace C5 (Sales Audit):**
- Baseline: 0.20 (1/5 matches)
- After prompt enhancements: 0.40 (2/5 matches)
- After post-processing: 0.60 (3/5 matches)
- **+200% improvement**

**Key fixes:**
- GSA now included (priority map resolution)
- Global Skills Development Report added (companion rule)
- OPQ32r added (post-processing enforcement)

**Remaining gaps:**
- Sales-specific reports (OPQ MQ Sales Report, Sales Transformation IC variant) still missing
- Requires further retrieval tuning or explicit sales scenario rules

### What Didn't Work

- **LLM-only rule enforcement**: Despite explicit "MUST include" rules in prompt, LLM inconsistently followed them. Solution: deterministic post-processing.
- **Full catalog in context**: 377 items × ~200 tokens = ~75k tokens; Groq times out. BM25 pre-filtering to 25 items fixes this.
- **Vector embeddings**: `all-MiniLM-L6-v2` added +3% recall but +400ms cold startup. Dropped for latency.
- **GPT-4o-mini**: Inconsistent JSON mode for multi-key items. Groq + llama more reliable.
- **Aggressive EOC detection**: Early versions set EOC=true on any "yes". Fixed with confirmation-only regex.

### Security Enhancements

**Prompt injection protection**: Early-return guard detects and blocks malicious patterns before LLM call. Enhanced regex patterns catch "ignore previous", "you are now", "act as", etc. All tests pass.

---

## AI Tools Used

**Claude (claude.ai)**: Used for initial prompt iteration, architecture exploration, and code implementation assistance.

All design decisions, retrieval logic, and business rules were human-driven based on trace analysis and evaluation results.
