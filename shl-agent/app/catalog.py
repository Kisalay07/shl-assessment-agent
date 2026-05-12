"""
Catalog loading, BM25 indexing, and hallucination-safe resolution.

The catalog.json is bundled with the service (no runtime fetch needed).
Falls back to the SHL public URL only if catalog.json is absent.
"""
from __future__ import annotations

import difflib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# ── paths ────────────────────────────────────────────────────────────────────
BUNDLED_CATALOG = Path(__file__).parent.parent / "catalog.json"
CATALOG_URL = os.getenv(
    "CATALOG_URL",
    "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json",
)

# ── type mapping ─────────────────────────────────────────────────────────────
KEY_TO_LETTER: Dict[str, str] = {
    "Knowledge & Skills":          "K",
    "Personality & Behavior":      "P",
    "Ability & Aptitude":          "A",
    "Biodata & Situational Judgment": "B",
    "Competencies":                "C",
    "Development & 360":           "D",
    "Assessment Exercises":        "E",
    "Simulations":                 "S",
}
# Priority used to pick the *primary* type for single-letter field
TYPE_PRIORITY = ["P", "A", "K", "B", "C", "D", "S", "E"]


def _primary_type(keys: List[str]) -> str:
    letters = [KEY_TO_LETTER.get(k, "K") for k in keys]
    for t in TYPE_PRIORITY:
        if t in letters:
            return t
    return "K"


def _combined_type(keys: List[str]) -> str:
    """Return comma-joined letter codes for multi-key items (e.g. 'K,S')."""
    seen = []
    for k in keys:
        letter = KEY_TO_LETTER.get(k, "K")
        if letter not in seen:
            seen.append(letter)
    return ",".join(seen) if seen else "K"


# ── seniority keyword → SHL job-level mapping ────────────────────────────────
SENIORITY_MAP: Dict[str, List[str]] = {
    "cxo":        ["Executive"],
    "ceo":        ["Executive"],
    "cto":        ["Executive"],
    "coo":        ["Executive"],
    "executive":  ["Executive", "Director"],
    "director":   ["Director", "Executive"],
    "vp":         ["Executive", "Director"],
    "vice president": ["Executive", "Director"],
    "senior":     ["Mid-Professional", "Professional Individual Contributor"],
    "lead":       ["Mid-Professional", "Professional Individual Contributor"],
    "manager":    ["Manager", "Front Line Manager", "Supervisor"],
    "supervisor": ["Supervisor", "Front Line Manager"],
    "mid":        ["Mid-Professional"],
    "associate":  ["Mid-Professional", "Entry-Level"],
    "junior":     ["Entry-Level"],
    "entry":      ["Entry-Level"],
    "graduate":   ["Graduate"],
    "intern":     ["Entry-Level"],
    "frontline":  ["Front Line Manager", "Entry-Level"],
    "front-line": ["Front Line Manager"],
    "front line": ["Front Line Manager"],
}


def _tokenise(text: str) -> List[str]:
    return re.findall(r"[a-z0-9+#]+", text.lower())


def _build_doc(item: dict) -> str:
    """All searchable text fields concatenated for BM25."""
    parts = [
        item.get("name", ""),
        item.get("description", ""),
        item.get("job_levels_raw", ""),
        " ".join(item.get("keys", [])),
        item.get("languages_raw", ""),
    ]
    return " ".join(p for p in parts if p)


# ── priority assessment map for common assessments ──────────────────────────
# These assessments are frequently recommended and must resolve reliably
PRIORITY_ASSESSMENTS: Dict[str, Dict[str, any]] = {
    "opq32r": {
        "canonical_name": "Occupational Personality Questionnaire OPQ32r",
        "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
        "aliases": ["OPQ32r", "OPQ 32r", "Occupational Personality Questionnaire OPQ32r", "Occupational Personality Questionnaire"],
    },
    "gsa": {
        "canonical_name": "Global Skills Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/global-skills-assessment/",
        "aliases": ["GSA", "Global Skills Assessment"],
    },
    "verify_g_plus": {
        "canonical_name": "SHL Verify Interactive G+",
        "url": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
        "aliases": ["Verify G+", "SHL Verify Interactive G+", "Verify G Plus", "SHL Verify G+"],
    },
    "global_skills_dev": {
        "canonical_name": "Global Skills Development Report",
        "url": "https://www.shl.com/products/product-catalog/view/global-skills-development-report/",
        "aliases": ["Global Skills Development Report", "Global Skills Dev Report"],
    },
    "graduate_scenarios": {
        "canonical_name": "Graduate Scenarios",
        "url": "https://www.shl.com/products/product-catalog/view/graduate-scenarios/",
        "aliases": ["Graduate Scenarios"],
    },
    "opq_leadership": {
        "canonical_name": "OPQ Leadership Report",
        "url": "https://www.shl.com/products/product-catalog/view/opq-leadership-report/",
        "aliases": ["OPQ Leadership Report", "OPQ Leadership"],
    },
    "ucr_2": {
        "canonical_name": "OPQ Universal Competency Report 2.0",
        "url": "https://www.shl.com/products/product-catalog/view/opq-universal-competency-report-2-0/",
        "aliases": ["OPQ Universal Competency Report 2.0", "UCR 2.0", "Universal Competency Report 2.0"],
    },
    "dsi": {
        "canonical_name": "Dependability and Safety Instrument (DSI)",
        "url": "https://www.shl.com/products/product-catalog/view/dependability-and-safety-instrument-dsi/",
        "aliases": ["DSI", "Dependability and Safety Instrument", "Dependability and Safety Instrument (DSI)"],
    },
    "svar_us": {
        "canonical_name": "SVAR - Spoken English (US) (New)",
        "url": "https://www.shl.com/products/product-catalog/view/svar-spoken-english-us-new/",
        "aliases": ["SVAR - Spoken English (US) (New)", "SVAR Spoken English (US)", "SVAR US"],
    },
    "excel_365": {
        "canonical_name": "Microsoft Excel 365 - Essentials (New)",
        "url": "https://www.shl.com/products/product-catalog/view/microsoft-excel-365-essentials-new/",
        "aliases": ["Microsoft Excel 365 - Essentials (New)", "Microsoft Excel 365", "Excel 365"],
    },
}

# ── alias map for known trace name → catalog name mismatches ─────────────────
NAME_ALIASES: Dict[str, str] = {
    # trace name (lower)                              : catalog name (exact)
    "svar spoken english (us) (new)":                  "SVAR - Spoken English (US) (New)",
    "svar spoken english (uk) (new)":                  "SVAR - Spoken English (U.K.)",
    "svar spoken english (aus)":                       "SVAR - Spoken English (AUS)",
    "svar spoken english (indian accent) (new)":       "SVAR - Spoken English (Indian Accent) (New)",
    "entry level customer serv - retail & contact center":
        "Entry Level Customer Serv-Retail & Contact Center",
    "microsoft excel 365 (new)":                       "Microsoft Excel 365 - Essentials (New)",
    "shl verify interactive g+":                       "SHL Verify Interactive G+",
}


class CatalogStore:
    """Holds the full catalog with BM25 index and two lookup dicts."""

    def __init__(self) -> None:
        self.items: List[dict] = []
        self.by_url:  Dict[str, dict] = {}
        self.by_name: Dict[str, dict] = {}   # lower-cased key → item
        self._bm25: Optional[BM25Okapi] = None

    # ── load ─────────────────────────────────────────────────────────────────
    async def load(self) -> None:
        raw = await self._read_catalog()
        self.items = raw
        self._build_indexes()
        logger.info("Catalog ready: %d items", len(self.items))

    async def _read_catalog(self) -> List[dict]:
        # Prefer bundled file (ships with the docker image)
        if BUNDLED_CATALOG.exists():
            logger.info("Loading bundled catalog from %s", BUNDLED_CATALOG)
            text = BUNDLED_CATALOG.read_text(encoding="utf-8", errors="replace")
            return json.loads(text, strict=False)

        # Fallback: fetch from SHL public URL
        import httpx
        logger.info("Fetching catalog from %s", CATALOG_URL)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(CATALOG_URL)
            resp.raise_for_status()
            return resp.json()

    # ── index ─────────────────────────────────────────────────────────────────
    def _build_indexes(self) -> None:
        tokenised: List[List[str]] = []
        for item in self.items:
            keys = item.get("keys", [])
            item["_type"]    = _primary_type(keys)
            item["_type_str"] = _combined_type(keys)
            url = item.get("link", "")
            self.by_url[url.rstrip("/")] = item
            self.by_name[item["name"].lower()] = item
            tokenised.append(_tokenise(_build_doc(item)))
        self._bm25 = BM25Okapi(tokenised)

    # ── search ────────────────────────────────────────────────────────────────
    def search(self, query: str, top_k: int = 25) -> List[dict]:
        if not self._bm25:
            return self.items[:top_k]
        tokens = _tokenise(query)
        if not tokens:
            return self.items[:top_k]
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.items[i] for i in ranked[:top_k]]

    def detect_levels(self, text: str) -> List[str]:
        """Map conversational seniority language to SHL job-level strings."""
        text_lower = text.lower()
        found: List[str] = []
        for kw, levels in SENIORITY_MAP.items():
            # word-start boundary; allow plural suffix
            if re.search(r"\b" + re.escape(kw) + r"(s|es)?\b", text_lower):
                found.extend(levels)
        return list(dict.fromkeys(found))

    def boost(self, results: List[dict], levels: List[str], top_k: int) -> List[dict]:
        """Interleave level-matching items to top of BM25 results."""
        if not levels:
            return results[:top_k]
        matching = [it for it in results if any(lv in it.get("job_levels", []) for lv in levels)]
        other    = [it for it in results if it not in matching]
        out: List[dict] = []
        mi = oi = 0
        while len(out) < top_k:
            for _ in range(3):
                if mi < len(matching): out.append(matching[mi]); mi += 1
            if oi < len(other):       out.append(other[oi]);    oi += 1
            if mi >= len(matching) and oi >= len(other):
                break
        return out[:top_k]

    # ── hallucination guard ───────────────────────────────────────────────────
    def resolve(self, name: str, url: str) -> Optional[dict]:
        """
        Return the real catalog item for an LLM-proposed recommendation.
        Returns None if no match → item is a hallucination and must be dropped.

        Resolution order:
          1. Exact URL match
          2. URL match with/without trailing slash
          3. Priority assessment map (by alias)
          4. Exact name match (case-insensitive)
          5. Known alias match
          6. Difflib close match (cutoff 0.82)
        """
        # 1 & 2: URL
        url_key = url.rstrip("/")
        if url_key in self.by_url:
            return self.by_url[url_key]

        # 3: Priority assessment map (NEW)
        name_lower = name.lower().strip()
        for key, priority_item in PRIORITY_ASSESSMENTS.items():
            for alias in priority_item["aliases"]:
                if alias.lower() == name_lower:
                    canonical = priority_item["canonical_name"].lower()
                    if canonical in self.by_name:
                        logger.info("Priority map resolved: %s → %s", name, canonical)
                        return self.by_name[canonical]
                    else:
                        logger.error("Priority assessment not found in catalog: %s", canonical)

        # 4: exact name
        name_key = name.lower().strip()
        if name_key in self.by_name:
            return self.by_name[name_key]

        # 5: alias
        if name_key in NAME_ALIASES:
            canon = NAME_ALIASES[name_key].lower()
            if canon in self.by_name:
                return self.by_name[canon]

        # 6: difflib on name
        close = difflib.get_close_matches(name_key, list(self.by_name.keys()), n=1, cutoff=0.82)
        if close:
            logger.debug("Fuzzy resolve: '%s' → '%s'", name, close[0])
            return self.by_name[close[0]]

        logger.warning("Hallucination filtered: name=%r url=%r", name, url)
        return None
