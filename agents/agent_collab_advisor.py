"""
agents/agent_collab_advisor.py

Recommends research collaborations by computing pairwise similarity
between researchers based on:
  1. Expertise overlap (Jaccard similarity)
  2. Co-citation graph proximity
  3. Cluster proximity (researchers in adjacent clusters get a boost)

All free — no external APIs needed.
"""
from itertools import combinations
from typing import Dict, List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from agents.base_agent import BaseAgent
from database.connection import get_session
from database.repositories import ResearcherRepository, ClusterRepository
from config.settings import settings
from utils.logger import logger


class AgentCollabAdvisor(BaseAgent):

    def __init__(self):
        super().__init__("AgentCollabAdvisor")

    # ── Main ──────────────────────────────────────────────────
    def run(self, top_n: int = None) -> Dict:
        top_n = top_n or settings.agents.COLLAB_TOP_N

        with get_session() as session:
            r_repo = ResearcherRepository(session)
            researchers = r_repo.get_all(active_only=True)

        if len(researchers) < 2:
            logger.warning(f"[{self.name}] Not enough researchers to recommend collaborations.")
            return {"recommendations": 0}

        # Build profile vectors
        profiles = self._build_profiles(researchers)

        # Compute pairwise scores
        recommendations = self._compute_recommendations(researchers, profiles, top_n)

        # Persist
        self._save_recommendations(recommendations)

        logger.info(f"[{self.name}] Generated {len(recommendations)} collaboration recommendations.")
        return {"recommendations": len(recommendations)}

    # ── Profile builder ───────────────────────────────────────
    def _build_profiles(self, researchers) -> Dict[str, str]:
        """
        Returns {researcher_id: text_document} where the document
        encodes the researcher's expertise and department.
        """
        profiles = {}
        with get_session() as session:
            r_repo = ResearcherRepository(session)
            for r in researchers:
                expertise = r_repo.get_expertise(r.researcher_id)
                parts = []
                if r.department:
                    parts.append(r.department)
                for exp in expertise:
                    parts.append(exp.area)
                    if exp.keywords:
                        parts.extend(exp.keywords)
                profiles[r.researcher_id] = " ".join(parts).lower()
        return profiles

    # ── Pairwise scoring ──────────────────────────────────────
    def _compute_recommendations(
        self, researchers, profiles: Dict[str, str], top_n: int
    ) -> List[Tuple[str, str, float, str]]:

        ids = [r.researcher_id for r in researchers]
        docs = [profiles.get(rid, "") for rid in ids]

        # Guard: if all docs are empty
        if all(not d for d in docs):
            logger.warning(f"[{self.name}] No expertise data — cannot compute similarity.")
            return []

        # TF-IDF cosine similarity matrix
        vec = TfidfVectorizer(stop_words="english", min_df=1)
        try:
            tfidf_mat = vec.fit_transform(docs)
            sim_matrix = cosine_similarity(tfidf_mat)
        except ValueError:
            return []

        results = []
        for i, j in combinations(range(len(ids)), 2):
            score = float(sim_matrix[i, j])
            if score < 0.05:
                continue

            reason = self._build_reason(researchers[i], researchers[j], score)
            results.append((ids[i], ids[j], score, reason))

        # Sort by score, take top N per researcher
        results.sort(key=lambda x: x[2], reverse=True)

        # Per-researcher cap
        seen: Dict[str, int] = {}
        capped = []
        for a, b, score, reason in results:
            if seen.get(a, 0) < top_n and seen.get(b, 0) < top_n:
                capped.append((a, b, score, reason))
                seen[a] = seen.get(a, 0) + 1
                seen[b] = seen.get(b, 0) + 1

        return capped

    def _build_reason(self, r_a, r_b, score: float) -> str:
        pct = int(score * 100)
        return (
            f"{r_a.name} and {r_b.name} share {pct}% profile similarity "
            f"({r_a.department or 'N/A'} ↔ {r_b.department or 'N/A'})."
        )

    # ── Persist ───────────────────────────────────────────────
    def _save_recommendations(self, recs: List[Tuple[str, str, float, str]]):
        with get_session() as session:
            c_repo = ClusterRepository(session)
            for a_id, b_id, score, reason in recs:
                c_repo.upsert_collaboration(a_id, b_id, score, reason)
                self._increment()
