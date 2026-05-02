"""
agents/agent_coordinator.py

Orchestrates the full MAS pipeline:
  1. AgentLabScraper        — discover / load labs
  2. AgentResearcherScraper — discover researchers automatically (OpenAlex)
  3. AgentPublicationScraper — fetch publications (OpenAlex)
  4. AgentExpertiseMatcher  — infer expertise from publications
  5. AgentCluster           — cluster researchers (K-Means)
  6. AgentCollabAdvisor     — recommend collaborations
  7. AgentNegotiator        — simulate negotiations (Game Theory)
"""
import time
from typing import Dict, List

from agents.base_agent import BaseAgent
from agents.agent_lab_scraper import AgentLabScraper
from agents.agent_researcher_scraper import AgentResearcherScraper
from agents.agent_publication_scraper import AgentPublicationScraper
from agents.agent_expertise_matcher import AgentExpertiseMatcher
from agents.agent_cluster import AgentCluster
from agents.agent_collab_advisor import AgentCollabAdvisor
from agents.agent_negotiator import AgentNegotiator
from config.settings import settings
from utils.logger import logger


class AgentCoordinator(BaseAgent):

    def __init__(self):
        super().__init__("AgentCoordinator")
        self.lab_scraper         = AgentLabScraper()
        self.researcher_scraper  = AgentResearcherScraper()
        self.publication_scraper = AgentPublicationScraper()
        self.expertise_matcher   = AgentExpertiseMatcher()
        self.cluster_agent       = AgentCluster()
        self.collab_advisor      = AgentCollabAdvisor()
        self.negotiator          = AgentNegotiator()

    # ── Main ──────────────────────────────────────────────────
    def run(
        self,
        country_code: str = None,
        institution_name: str = None,
        topic: str = None,
        seed_researchers: List[str] = None,
        seed_labs: List[Dict] = None,
        university_url: str = None,
        skip_scrape: bool = False,
        n_clusters: int = None,
        max_authors: int = None,
    ) -> Dict:
        """
        Full pipeline.

        Discovery — pick at least one option (all optional):
          country_code:     ISO code e.g. "TN", "FR", "DZ"
          institution_name: e.g. "Universite de Tunis El Manar"
          topic:            e.g. "machine learning", "NLP"
          seed_researchers: Fallback list of researcher names
          seed_labs:        Manual list of lab dicts to insert
          university_url:   URL to scrape for lab names

        Use skip_scrape=True to re-run only analysis on existing DB data.
        """
        report = {}
        logger.info("=" * 60)
        logger.info("[AgentCoordinator] Pipeline START")
        logger.info("=" * 60)

        # ── Phase 1: Data Collection ───────────────────────────
        if not skip_scrape:
            logger.info("[Phase 1] Data Collection")

            lab_result = self._run_agent(
                self.lab_scraper,
                seed_labs=seed_labs or [],
                university_url=university_url,
            )
            report["labs"] = lab_result

            researcher_result = self._run_agent(
                self.researcher_scraper,
                country_code=country_code,
                institution_name=institution_name,
                topic=topic,
                seed_names=seed_researchers or [],
                max_authors=max_authors,
            )
            report["researchers"] = researcher_result

            pub_result = self._run_agent(self.publication_scraper)
            report["publications"] = pub_result
        else:
            logger.info("[Phase 1] Skipped (skip_scrape=True)")

        # ── Phase 2: Analysis ──────────────────────────────────
        logger.info("[Phase 2] Analysis")

        expertise_result = self._run_agent(self.expertise_matcher)
        report["expertise"] = expertise_result

        cluster_result = self._run_agent(self.cluster_agent, n_clusters=n_clusters)
        report["clusters"] = cluster_result

        # ── Phase 3: Recommendations ───────────────────────────
        logger.info("[Phase 3] Recommendations & Negotiation")

        collab_result = self._run_agent(self.collab_advisor)
        report["collaborations"] = collab_result

        negotiation_result = self._run_agent(self.negotiator)
        report["negotiations"] = negotiation_result

        logger.info("=" * 60)
        logger.info("[AgentCoordinator] Pipeline COMPLETE")
        logger.info(f"Summary: {report}")
        logger.info("=" * 60)

        return report

    # ── Agent runner with messaging ────────────────────────────
    def _run_agent(self, agent: BaseAgent, **kwargs) -> Dict:
        logger.info(f"[AgentCoordinator] Launching → {agent.name}")
        try:
            result = agent.start(**kwargs)
            self.receive_message(sender=agent.name, message={"status": "done", "result": result})
            return result
        except Exception as e:
            logger.error(f"[AgentCoordinator] {agent.name} failed: {e}")
            return {"error": str(e)}

    def receive_message(self, sender: str, message: Dict):
        logger.debug(f"[AgentCoordinator] <- [{sender}] {message.get('status', '?')}")
