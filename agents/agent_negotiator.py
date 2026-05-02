"""
agents/agent_negotiator.py

Simulates negotiation between researchers for collaboration
using Game Theory concepts:

  - Nash Bargaining Solution: both parties maximise joint utility
  - Rubinstein Alternating Offers: time-discounted offer/counter-offer
  - Shapley Value: fair resource (funding/project time) allocation

No external API required — pure Python/NumPy.
"""
from typing import Dict, List, Tuple, Optional
import numpy as np

from agents.base_agent import BaseAgent
from database.connection import get_session
from database.repositories import ClusterRepository, ResearcherRepository
from utils.logger import logger


class AgentNegotiator(BaseAgent):

    def __init__(self):
        super().__init__("AgentNegotiator")

    # ── Main ──────────────────────────────────────────────────
    def run(self, top_n_collabs: int = 20) -> Dict:
        """
        For each top collaboration pair, run a negotiation simulation
        and store the outcome in the collaboration record.
        """
        with get_session() as session:
            c_repo = ClusterRepository(session)
            collabs = c_repo.get_all_collaborations(limit=top_n_collabs)

        results = []
        for collab in collabs:
            outcome = self._negotiate(
                collab.researcher_a_id,
                collab.researcher_b_id,
                collab.score,
            )
            results.append(outcome)
            self._increment()
            logger.debug(
                f"[{self.name}] {collab.researcher_a_id[:8]}↔{collab.researcher_b_id[:8]} "
                f"→ {outcome['outcome']}"
            )

        agreements = sum(1 for r in results if r["outcome"] == "agreement")
        return {
            "negotiations_run": len(results),
            "agreements": agreements,
            "breakdowns": len(results) - agreements,
        }

    # ── Nash Bargaining Solution ──────────────────────────────
    def _nash_bargaining(
        self,
        utility_a: float,
        utility_b: float,
        disagreement_a: float = 0.0,
        disagreement_b: float = 0.0,
    ) -> Tuple[float, float]:
        """
        Maximise (u_a - d_a) * (u_b - d_b).
        Surplus is split so that both get at least disagreement payoff.
        """
        surplus = (utility_a - disagreement_a) + (utility_b - disagreement_b)
        if surplus <= 0:
            return disagreement_a, disagreement_b
        # Symmetric Nash solution: equal split of surplus
        offer_a = disagreement_a + surplus / 2
        offer_b = disagreement_b + surplus / 2
        return round(offer_a, 3), round(offer_b, 3)

    # ── Rubinstein Alternating Offers ─────────────────────────
    def _rubinstein_offers(
        self,
        total: float = 1.0,
        discount_a: float = 0.9,
        discount_b: float = 0.85,
        max_rounds: int = 10,
    ) -> Dict:
        """
        Simulates an alternating-offer bargaining game.
        Returns the round and split when an agreement is reached.
        """
        pie = total
        for round_num in range(1, max_rounds + 1):
            if round_num % 2 == 1:
                # Researcher A proposes
                a_share = pie / (1 + discount_b)
                b_share = pie - a_share
                # B accepts if b_share >= discount_b * pie_next_round
                if b_share >= discount_b * pie * discount_a:
                    return {"round": round_num, "proposer": "A", "share_a": round(a_share, 3), "share_b": round(b_share, 3)}
            else:
                # Researcher B proposes
                b_share = pie / (1 + discount_a)
                a_share = pie - b_share
                if a_share >= discount_a * pie * discount_b:
                    return {"round": round_num, "proposer": "B", "share_a": round(a_share, 3), "share_b": round(b_share, 3)}
            pie *= (discount_a * discount_b)  # shrinking pie

        return {"round": max_rounds, "proposer": None, "share_a": 0.0, "share_b": 0.0}

    # ── Shapley Value (simplified, 2-player) ─────────────────
    def _shapley_value(self, v_a: float, v_b: float, v_ab: float) -> Tuple[float, float]:
        """
        2-player Shapley value:
          phi_a = 0.5 * v_a + 0.5 * (v_ab - v_b)
          phi_b = 0.5 * v_b + 0.5 * (v_ab - v_a)
        """
        phi_a = 0.5 * v_a + 0.5 * (v_ab - v_b)
        phi_b = 0.5 * v_b + 0.5 * (v_ab - v_a)
        return round(phi_a, 3), round(phi_b, 3)

    # ── Full negotiation ──────────────────────────────────────
    def _negotiate(self, a_id: str, b_id: str, similarity_score: float) -> Dict:
        """
        Run all three models and aggregate an outcome.
        Utility is a function of the collaboration similarity score.
        """
        # Utility based on similarity (could be extended with grant budget, etc.)
        u_a = similarity_score * np.random.uniform(0.8, 1.2)
        u_b = similarity_score * np.random.uniform(0.8, 1.2)
        v_ab = (u_a + u_b) * 1.3  # synergy bonus

        nash_a, nash_b = self._nash_bargaining(u_a, u_b)
        rubinstein = self._rubinstein_offers(total=v_ab)
        phi_a, phi_b = self._shapley_value(u_a, u_b, v_ab)

        # Agreement if both Nash and Rubinstein converge
        reached = rubinstein["share_a"] > 0 and rubinstein["share_b"] > 0
        outcome = "agreement" if reached else "breakdown"

        return {
            "researcher_a": a_id,
            "researcher_b": b_id,
            "nash": {"a": nash_a, "b": nash_b},
            "rubinstein": rubinstein,
            "shapley": {"a": phi_a, "b": phi_b},
            "outcome": outcome,
        }
