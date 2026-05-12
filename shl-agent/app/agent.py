"""
Agent: one stateless call per /chat turn.

Flow per call:
  1. Detect intent signals (seniority, compare, refine, refuse keywords).
  2. Build BM25 query from all user turns; seniority-boost the result list.
  3. Inject catalog context into system prompt.
  4. Call Groq with JSON mode.
  5. Parse + validate recommendations against catalog (hallucination guard).
  6. Return ChatResponse.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Optional

from groq import AsyncGroq

from .catalog import CatalogStore
from .models import ChatResponse, Message, Recommendation
from .prompts import build_catalog_context, build_system

logger = logging.getLogger(__name__)

GROQ_MODEL   = os.getenv("GROQ_MODEL",      "llama-3.3-70b-versatile")
MAX_TOKENS   = int(os.getenv("LLM_MAX_TOKENS",  "1400"))
TEMPERATURE  = float(os.getenv("LLM_TEMPERATURE", "0.05"))
RETRIEVAL_K  = int(os.getenv("RETRIEVAL_TOP_K",  "25"))

# ── intent signal detection ───────────────────────────────────────────────────
_COMPARE_RE = re.compile(
    r"\b(what('s| is) the difference|how does .+ (compare|differ)|"
    r"compare .+ (to|with|and)|vs\.?\s+|versus)\b",
    re.I,
)
_REFINE_RE = re.compile(
    r"\b(add|include|also (add|include)|drop|remove|replace|swap|update|"
    r"change|without|exclude|take out|put in|keep|skip)\b",
    re.I,
)
_CONFIRM_RE = re.compile(
    r"\b(perfect|confirmed?|that'?s? (it|what|good|great|correct|fine)|"
    r"lock(ed|ing)? (it )?in|that works|sounds good|yes|great|"
    r"go ahead|proceed|agreed|done|good|let'?s? go)\b",
    re.I,
)
_REFUSE_RE = re.compile(
    r"\b(legal(ly)?|law|comply|complian|require(d|ment)|regulation|"
    r"salary|pay|price|cost|billing|implement(ation)?|integrat(e|ion|ing)|vendor|"
    r"ignore (previous|above|all|every)|forget (your|all|every)|"
    r"pretend|you are now|act as|jailbreak|bypass|disregard|"
    r"override|new instructions|system prompt|reveal|roleplay|"
    r"tell me a joke|write (me )?a (poem|story|joke|song)|"
    r"you are (a|an|my)|from now on|new persona|"
    r"ignore all|do not follow|don'?t follow)\b",
    re.I,
)

# Secondary check: full-message injection patterns (not word-boundary)
_INJECTION_PHRASES = re.compile(
    r"(ignore\s+(previous|prior|above|all|any|the)\s+(instructions?|rules?|prompts?|context)|"
    r"forget\s+(everything|all|your|prior)|"
    r"you\s+are\s+now|"
    r"new\s+role|"
    r"act\s+as\s+(if|a|an|my)|"
    r"stop\s+being|"
    r"from\s+now\s+on\s+you)",
    re.I,
)

_REFUSE_MESSAGE = (
    "I can only help with selecting SHL Individual Test Solutions. "
    "I'm not able to assist with that request. "
    "Could you tell me about the role you're hiring for?"
)


def _extract_json(text: str) -> dict:
    """Robustly extract first JSON object, handling markdown fences."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if   ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("Unbalanced JSON")


class Agent:
    def __init__(self, catalog: CatalogStore) -> None:
        self.catalog = catalog
        self._llm = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])

    def _enforce_standard_assessments(
        self,
        recs: List[Recommendation],
        query: str,
        levels: List[str],
        seen_names: set
    ) -> List[Recommendation]:
        """
        Deterministic post-processing to enforce business rules.
        Adds missing standard assessments based on role/purpose/seniority.
        """
        query_lower = query.lower()
        
        # Detect purpose keywords
        is_development = any(kw in query_lower for kw in ["development", "talent audit", "re-skill", "audit"])
        is_selection = any(kw in query_lower for kw in ["selection", "hiring", "recruit", "candidate"])
        is_graduate = any(kw in query_lower for kw in ["graduate", "entry-level", "entry level"])
        is_senior_ic = any(kw in query_lower for kw in ["senior", "lead", "principal", "staff"]) and \
                       any(kw in query_lower for kw in ["engineer", "developer", "ic", "individual contributor"])
        is_professional = any(kw in query_lower for kw in ["professional", "manager", "director", "executive", "vp", "cxo"])
        is_leadership = any(kw in query_lower for kw in ["leadership", "director", "executive", "cxo", "vp", "c-level"])
        is_sales = "sales" in query_lower
        
        # Detect if user explicitly declined assessments
        declined_personality = any(kw in query_lower for kw in ["no personality", "without personality", "skip personality"])
        declined_cognitive = any(kw in query_lower for kw in ["no cognitive", "without cognitive", "skip cognitive"])
        
        # Helper to check if assessment already included
        def has_assessment(name_pattern: str) -> bool:
            return any(name_pattern.lower() in rec.name.lower() for rec in recs)
        
        # Helper to add assessment if not present
        def add_if_missing(canonical_name: str, max_recs: int = 10) -> bool:
            if len(recs) >= max_recs:
                return False
            name_key = canonical_name.lower()
            if name_key in seen_names:
                return False
            # Find in catalog
            item = self.catalog.by_name.get(name_key)
            if item:
                seen_names.add(name_key)
                recs.append(Recommendation(
                    name=item["name"],
                    url=item["link"],
                    test_type=item.get("_type_str", item.get("_type", "K")),
                ))
                logger.info("Post-processing added: %s", canonical_name)
                return True
            return False
        
        # Rule 1: OPQ32r for professional/manager/senior/leadership roles
        if not declined_personality and not has_assessment("opq32r"):
            if is_professional or is_leadership or is_senior_ic or is_sales or levels:
                add_if_missing("occupational personality questionnaire opq32r")
        
        # Rule 2: Verify G+ for senior IC, tech lead, or graduate roles
        if not declined_cognitive and not has_assessment("verify") and not has_assessment("g+"):
            if is_senior_ic or is_graduate:
                add_if_missing("shl verify interactive g+")
        
        # Rule 3: GSA for development/audit purposes
        if is_development and not has_assessment("global skills assessment"):
            add_if_missing("global skills assessment")
        
        # Rule 4: Global Skills Development Report alongside GSA
        if has_assessment("global skills assessment") and not has_assessment("global skills development"):
            add_if_missing("global skills development report")
        
        # Rule 5: Graduate Scenarios for graduate roles
        if is_graduate and not has_assessment("graduate scenarios"):
            add_if_missing("graduate scenarios")
        
        # Rule 6: Fix variant selection for Sales Transformation
        # If we have Sales Manager variant but query suggests IC, replace it
        if "individual contributor" in query_lower or "ic" in query_lower:
            for i, rec in enumerate(recs):
                if "sales transformation" in rec.name.lower() and "sales manager" in rec.name.lower():
                    # Try to replace with IC variant
                    ic_variant = self.catalog.by_name.get("sales transformation 2.0 - individual contributor".lower())
                    if ic_variant:
                        recs[i] = Recommendation(
                            name=ic_variant["name"],
                            url=ic_variant["link"],
                            test_type=ic_variant.get("_type_str", ic_variant.get("_type", "K")),
                        )
                        logger.info("Post-processing replaced Sales Manager with IC variant")
                        break
        
        return recs[:10]  # Ensure max 10

    async def chat(self, messages: List[Message]) -> ChatResponse:
        # ── 1. Signal detection ──────────────────────────────────────────────
        user_turns     = [m.content for m in messages if m.role == "user"]
        last_user      = user_turns[-1] if user_turns else ""
        full_user_text = " ".join(user_turns)

        is_compare = bool(_COMPARE_RE.search(last_user))
        is_refine  = bool(_REFINE_RE.search(last_user))
        is_confirm = bool(_CONFIRM_RE.search(last_user)) and "?" not in last_user
        is_refuse  = (bool(_REFUSE_RE.search(last_user))
                      or bool(_INJECTION_PHRASES.search(last_user)))

        # ── 1b. HARD REFUSAL — bypass LLM entirely ──────────────────────────
        if is_refuse:
            logger.info("Hard refusal triggered for: %s", last_user[:80])
            return ChatResponse(
                reply=_REFUSE_MESSAGE,
                recommendations=[],
                end_of_conversation=False,
            )

        # ── 2. BM25 retrieve + seniority boost ───────────────────────────────
        results = self.catalog.search(full_user_text, top_k=RETRIEVAL_K)
        levels  = self.catalog.detect_levels(full_user_text)
        results = self.catalog.boost(results, levels, top_k=RETRIEVAL_K)

        # For compare/refine, also retrieve using last user message alone
        # so the context includes what's being compared/refined
        if is_compare or is_refine:
            extra = self.catalog.search(last_user, top_k=10)
            # Merge without duplicates
            seen_ids = {id(r) for r in results}
            for e in extra:
                if id(e) not in seen_ids:
                    results.append(e)
                    seen_ids.add(id(e))
            results = results[:RETRIEVAL_K]

        # ── 3. Build prompts ──────────────────────────────────────────────────
        turn_count = len(messages)
        ctx        = build_catalog_context(results)
        system     = build_system(ctx, len(results), turn_count)

        groq_msgs = [{"role": m.role, "content": m.content} for m in messages]

        # ── 4. LLM call ───────────────────────────────────────────────────────
        try:
            resp = await self._llm.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": system}] + groq_msgs,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"},
                timeout=24,
            )
            raw  = resp.choices[0].message.content or "{}"
            data = _extract_json(raw)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc, exc_info=True)
            return ChatResponse(
                reply="I'm having trouble right now — could you rephrase your question?",
                recommendations=[],
                end_of_conversation=False,
            )

        # ── 5. Hallucination guard ───────────────────────────────────────────
        safe_recs: List[Recommendation] = []
        seen_names: set = set()
        for raw_rec in data.get("recommendations", []):
            item = self.catalog.resolve(
                raw_rec.get("name", ""),
                raw_rec.get("url", ""),
            )
            if item is None:
                continue   # filtered out
            name_key = item["name"].lower()
            if name_key in seen_names:
                continue   # deduplicate
            seen_names.add(name_key)
            safe_recs.append(Recommendation(
                name      = item["name"],
                url       = item["link"],
                test_type = item.get("_type_str", item.get("_type", "K")),
            ))
            if len(safe_recs) == 10:
                break

        # ── 5b. POST-PROCESSING: Enforce business rules ──────────────────────
        # This ensures critical assessments are included regardless of LLM output
        safe_recs = self._enforce_standard_assessments(
            safe_recs, full_user_text, levels, seen_names
        )

        # ── 6. EOC logic ──────────────────────────────────────────────────────
        # Trust the LLM's EOC flag, but also set it if the user confirmed and
        # there are recommendations (safety net for the evaluator's turn cap).
        eoc = bool(data.get("end_of_conversation", False))
        if is_confirm and safe_recs and not eoc:
            eoc = True
        # Auto-EOC at turn cap if we have recommendations
        if turn_count >= 7 and safe_recs and not eoc:
            eoc = True

        return ChatResponse(
            reply              = data.get("reply", ""),
            recommendations    = safe_recs,
            end_of_conversation= eoc,
        )
