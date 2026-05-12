"""
Offline evaluation harness — replays all 10 traces and computes Recall@10.

Usage:
  python eval.py                         # all traces in traces/
  python eval.py --trace traces/C1.json  # single trace
  python eval.py --url http://host:8000  # override agent URL

The harness uses a cheap Groq model to simulate the user.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import statistics
from pathlib import Path
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

AGENT_URL  = os.getenv("AGENT_URL", "http://localhost:8000")
SIM_MODEL  = os.getenv("EVAL_MODEL", "llama-3.1-8b-instant")
MAX_TURNS  = 8   # spec hard cap


# ── simulated user ────────────────────────────────────────────────────────────
SIM_SYSTEM = """\
You are simulating a hiring manager talking to an SHL assessment consultant chatbot.

Persona: {persona}
Facts (answer ONLY from these; say "I have no particular preference" for anything else):
{facts}

Rules:
- Be truthful and brief (1-3 sentences per reply).
- Volunteer ONLY what was asked. Do not dump all facts at once.
- When the agent provides a final shortlist and asks if it's acceptable, reply:
  "Perfect, that works for us."
- If asked something outside your facts, say "I have no particular preference."
"""

async def sim_user_reply(client: AsyncGroq, persona: str, facts: dict, conversation: list) -> str:
    resp = await client.chat.completions.create(
        model=SIM_MODEL,
        messages=[
            {"role": "system", "content": SIM_SYSTEM.format(
                persona=persona, facts=json.dumps(facts, indent=2)
            )}
        ] + conversation,
        temperature=0.2,
        max_tokens=150,
    )
    return resp.choices[0].message.content.strip()


# ── agent call ────────────────────────────────────────────────────────────────
async def call_agent(http: httpx.AsyncClient, messages: list) -> dict:
    resp = await http.post(
        f"{AGENT_URL}/chat",
        json={"messages": messages},
        timeout=35,
    )
    resp.raise_for_status()
    return resp.json()


# ── Recall@K ──────────────────────────────────────────────────────────────────
def recall_at_k(recommended: List[str], expected: List[str], k: int = 10) -> float:
    if not expected:
        return 1.0
    top_k = {r.lower() for r in recommended[:k]}
    hits  = sum(1 for e in expected if e.lower() in top_k)
    return hits / len(expected)


# ── single trace ──────────────────────────────────────────────────────────────
async def run_trace(trace: dict, groq: AsyncGroq, http: httpx.AsyncClient, name: str = "") -> float:
    persona   = trace.get("persona", "")
    facts     = trace.get("facts", {})
    expected  = trace.get("expected", [])
    opening   = trace.get("opening", "")

    # Generate opening if not set
    if not opening:
        r = await groq.chat.completions.create(
            model=SIM_MODEL,
            messages=[
                {"role": "system", "content": SIM_SYSTEM.format(
                    persona=persona, facts=json.dumps(facts)
                )},
                {"role": "user", "content": "Start the conversation with your initial request."},
            ],
            temperature=0.3, max_tokens=80,
        )
        opening = r.choices[0].message.content.strip()

    conversation: List[dict] = [{"role": "user", "content": opening}]
    final_recs: List[str]    = []

    for _ in range(MAX_TURNS // 2 + 1):
        agent_resp  = await call_agent(http, conversation)
        agent_reply = agent_resp.get("reply", "")
        recs        = agent_resp.get("recommendations", [])
        eoc         = agent_resp.get("end_of_conversation", False)

        conversation.append({"role": "assistant", "content": agent_reply})

        if recs:
            final_recs = [r["name"] for r in recs]

        if eoc or len(conversation) >= MAX_TURNS:
            break

        user_reply = await sim_user_reply(groq, persona, facts, conversation)
        conversation.append({"role": "user", "content": user_reply})

        if recs and any(kw in user_reply.lower() for kw in
                ("perfect", "great", "confirmed", "works", "yes", "good", "done", "lock")):
            break

    r10 = recall_at_k(final_recs, expected)
    logger.info("[%s] Recall@10=%.2f | got=%s | expected=%s",
                name, r10, final_recs[:5], expected)
    return r10


# ── main ──────────────────────────────────────────────────────────────────────
async def main(paths: List[Path]) -> None:
    groq   = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
    scores: List[float] = []

    async with httpx.AsyncClient() as http:
        for path in paths:
            trace = json.loads(path.read_text())
            score = await run_trace(trace, groq, http, path.stem)
            scores.append(score)

    print(f"\n{'='*55}")
    print(f"Traces evaluated  : {len(scores)}")
    print(f"Mean Recall@10    : {statistics.mean(scores):.3f}")
    if len(scores) > 1:
        print(f"Std dev           : {statistics.stdev(scores):.3f}")
        print(f"Min / Max         : {min(scores):.2f} / {max(scores):.2f}")
        for i, (p, s) in enumerate(zip(paths, scores), 1):
            print(f"  {i:>2}. {p.stem:<40} {s:.2f}")
    print(f"{'='*55}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", default="traces", help="Folder of trace JSON files")
    parser.add_argument("--trace",  default=None,     help="Single trace file")
    parser.add_argument("--url",    default=None,     help="Override agent URL")
    args = parser.parse_args()

    if args.url:
        AGENT_URL = args.url

    if args.trace:
        paths = [Path(args.trace)]
    else:
        paths = sorted(Path(args.traces).glob("*.json"))

    if not paths:
        print("No trace files found."); exit(1)

    asyncio.run(main(paths))
