"""
agents/agent_expertise_matcher.py

Infers expertise areas for each researcher from their publication titles
using TF-IDF keyword extraction, then stores them in the `expertise` table.

No paid API required.
"""
from typing import List, Dict, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from agents.base_agent import BaseAgent
from database.connection import get_session
from database.repositories import ResearcherRepository, PublicationRepository
from utils.logger import logger


# Broad predefined expertise domains — extend as needed
EXPERTISE_DOMAINS = {
    "Machine Learning": ["machine learning", "deep learning", "neural network", "classification", "regression", "reinforcement learning"],
    "Natural Language Processing": ["nlp", "text", "language model", "sentiment", "named entity", "transformer", "bert"],
    "Computer Vision": ["image", "vision", "object detection", "segmentation", "cnn", "visual"],
    "Bioinformatics": ["genomics", "protein", "bioinformatics", "dna", "rna", "sequence alignment"],
    "Cybersecurity": ["security", "cryptography", "intrusion detection", "malware", "vulnerability", "encryption"],
    "Distributed Systems": ["distributed", "cloud", "microservice", "kubernetes", "consensus", "fault tolerance"],
    "Databases": ["database", "sql", "nosql", "query", "indexing", "data warehouse"],
    "Robotics": ["robot", "autonomous", "navigation", "control system", "kinematics"],
    "Quantum Computing": ["quantum", "qubit", "quantum algorithm", "superposition"],
    "Networks": ["network", "routing", "protocol", "wireless", "5g", "iot"],
    "Optimization": ["optimization", "genetic algorithm", "evolutionary", "metaheuristic", "linear programming"],
    "Software Engineering": ["software", "agile", "testing", "devops", "refactoring", "architecture"],
}


class AgentExpertiseMatcher(BaseAgent):

    def __init__(self):
        super().__init__("AgentExpertiseMatcher")

    # ── Main ──────────────────────────────────────────────────
    def run(self, researcher_ids: List[str] = None) -> Dict:
        with get_session() as session:
            r_repo = ResearcherRepository(session)
            researchers = (
                [r_repo.get_by_id(rid) for rid in researcher_ids]
                if researcher_ids
                else r_repo.get_all(active_only=True)
            )
            researchers = [r for r in researchers if r]

        total = 0
        for researcher in researchers:
            areas = self._infer_expertise(researcher.researcher_id)
            self._save_expertise(researcher.researcher_id, areas)
            total += len(areas)
            self._increment()
            logger.debug(f"[{self.name}] {researcher.name}: {[a for a, _ in areas]}")

        return {"researchers_processed": len(researchers), "expertise_entries": total}

    # ── Inference ─────────────────────────────────────────────
    def _infer_expertise(self, researcher_id: str) -> List[Tuple[str, List[str]]]:
        """Returns list of (area, matched_keywords) tuples."""
        with get_session() as session:
            pub_repo = PublicationRepository(session)
            pubs = pub_repo.get_by_researcher(researcher_id)

        if not pubs:
            return []

        # Build researcher document
        full_text = " ".join(
            f"{p.title or ''} {p.abstract or ''}" for p in pubs
        ).lower()

        matched = []
        for domain, keywords in EXPERTISE_DOMAINS.items():
            hits = [kw for kw in keywords if kw in full_text]
            if len(hits) >= 2:  # at least 2 keyword matches to confirm domain
                matched.append((domain, hits))

        # Also extract top TF-IDF keywords as free-form expertise
        top_kws = self._extract_top_keywords(full_text)
        if top_kws:
            matched.append(("Research Keywords", top_kws))

        return matched

    def _extract_top_keywords(self, text: str, top_n: int = 10) -> List[str]:
        if not text.strip():
            return []
        try:
            vec = TfidfVectorizer(
                max_features=200,
                stop_words="english",
                ngram_range=(1, 2),
            )
            mat = vec.fit_transform([text])
            scores = mat.toarray()[0]
            top_idx = np.argsort(scores)[-top_n:][::-1]
            return [vec.get_feature_names_out()[i] for i in top_idx if scores[i] > 0]
        except Exception:
            return []

    # ── Persist ───────────────────────────────────────────────
    def _save_expertise(self, researcher_id: str, areas: List[Tuple[str, List[str]]]):
        with get_session() as session:
            r_repo = ResearcherRepository(session)
            for area, keywords in areas:
                r_repo.upsert_expertise(
                    researcher_id=researcher_id,
                    area=area,
                    keywords=keywords,
                    score=len(keywords) / 10.0,
                    source="inferred",
                )
