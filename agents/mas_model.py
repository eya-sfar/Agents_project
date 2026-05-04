"""
agents/mas_model.py

Modèle Mesa central — orchestre tous les agents MAS.

Mesa 3.x : mesa.Model est le conteneur qui gère le scheduler et
les agents. Chaque tick (step) fait avancer un agent dans la pipeline.

Architecture :
  Tick 1 → AgentLabScraper.step()
  Tick 2 → AgentResearcherScraper.step()
  Tick 3 → AgentPublicationScraper.step()
  Tick 4 → AgentExpertiseMatcher.step()  (wrappé)
  Tick 5 → AgentCluster.step()           (wrappé)
  Tick 6 → AgentCollabAdvisor.step()     (wrappé)
  Tick 7 → AgentNegotiator.step()        (wrappé)

Usage :
  from agents.mas_model import ObservatoryModel
  model = ObservatoryModel(country_code="TN")
  model.run_pipeline()          # exécute tous les ticks
  print(model.report)           # résultats complets
"""
from typing import Dict, List, Optional, Any

import mesa

from utils.logger import logger

# ─── Scrapers Mesa ────────────────────────────────────────────
from agents.agent_lab_scraper         import AgentLabScraper
from agents.agent_researcher_scraper  import AgentResearcherScraper
from agents.agent_publication_scraper import AgentPublicationScraper

# ─── Agents analyse (wrappés en Mesa) ─────────────────────────
from agents.mesa_wrappers import (
    AgentExpertiseMatcherMesa,
    AgentClusterMesa,
    AgentCollabAdvisorMesa,
    AgentNegotiatorMesa,
)


class ObservatoryModel(mesa.Model):
    """
    Modèle Mesa principal de l'Observatoire.

    Paramètres de découverte (tous optionnels — au moins un requis) :
      country_code     : "TN", "FR", "DZ" ou nom complet "Tunisia"
      institution_name : "Université de Tunis El Manar"
      topic            : "machine learning", "NLP Arabic"
      seed_researchers : ["Alice Smith", "Bob Jones"]   # fallback noms
      seed_labs        : [{"name": "AI Lab", "country": "TN"}, ...]
      university_url   : "https://www.fst.utm.tn/laboratoires"

    Paramètres pipeline :
      skip_scrape  : True → saute la collecte, relance seulement l'analyse
      n_clusters   : nombre de clusters K-Means (défaut: 8)
      max_authors  : max chercheurs à importer (défaut: 200)
      max_pages    : pages OpenAlex par agent (défaut: 5 = 125 résultats)
    """

    def __init__(
        self,
        # Découverte
        country_code:     Optional[str]       = None,
        institution_name: Optional[str]       = None,
        topic:            Optional[str]       = None,
        seed_researchers: Optional[List[str]] = None,
        seed_labs:        Optional[List[Dict]] = None,
        university_url:   Optional[str]       = None,
        # Pipeline
        skip_scrape:  bool = False,
        n_clusters:   int  = 8,
        max_authors:  int  = 200,
        max_pages:    int  = 5,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.skip_scrape = skip_scrape
        self.report: Dict[str, Any] = {}
        self._pipeline_done: Dict[str, bool] = {}

        # ── Créer les agents Mesa ──────────────────────────────
        # Scrapers
        self.lab_scraper   = AgentLabScraper(model=self, max_pages=max_pages)
        self.res_scraper   = AgentResearcherScraper(model=self, max_pages=max_pages)
        self.pub_scraper   = AgentPublicationScraper(model=self, max_pages=max_pages)

        # Analyse (wrappés)
        self.expertise     = AgentExpertiseMatcherMesa(model=self)
        self.cluster       = AgentClusterMesa(model=self, n_clusters=n_clusters)
        self.collab        = AgentCollabAdvisorMesa(model=self)
        self.negotiator    = AgentNegotiatorMesa(model=self)

        # ── Injecter les paramètres dans les scrapers ──────────
        self.lab_scraper.seed_labs        = seed_labs or []
        self.lab_scraper.university_url   = university_url
        self.lab_scraper.country_code     = country_code

        self.res_scraper.country_code     = country_code
        self.res_scraper.institution_name = institution_name
        self.res_scraper.topic            = topic
        self.res_scraper.seed_names       = seed_researchers or []
        self.res_scraper.max_authors      = max_authors

        # ── Pipeline ordonné (séquentiel) ─────────────────────
        if skip_scrape:
            self._pipeline = [
                self.expertise,
                self.cluster,
                self.collab,
                self.negotiator,
            ]
        else:
            self._pipeline = [
                self.lab_scraper,
                self.res_scraper,
                self.pub_scraper,
                self.expertise,
                self.cluster,
                self.collab,
                self.negotiator,
            ]

        self._current_tick = 0
        logger.info(f"[ObservatoryModel] Initialized — {len(self._pipeline)} agents in pipeline")

    # ─────────────────────────────────────────────────────────
    # Mesa step — avance d'un tick (un agent à la fois)
    # ─────────────────────────────────────────────────────────
    def step(self):
        if self._current_tick >= len(self._pipeline):
            logger.info("[ObservatoryModel] Pipeline already complete.")
            return

        agent = self._pipeline[self._current_tick]
        phase = "Scraping" if self._current_tick < 3 and not self.skip_scrape else "Analysis"
        logger.info(
            f"[ObservatoryModel] ── Tick {self._current_tick + 1}/{len(self._pipeline)} "
            f"[{phase}] → {agent.__class__.__name__}"
        )
        agent.step()
        self._current_tick += 1

    # ─────────────────────────────────────────────────────────
    # run_pipeline — exécute tous les ticks d'un coup
    # ─────────────────────────────────────────────────────────
    def run_pipeline(self) -> Dict:
        logger.info("=" * 60)
        logger.info("[ObservatoryModel] PIPELINE START")
        logger.info("=" * 60)

        for _ in range(len(self._pipeline)):
            self.step()

        logger.info("=" * 60)
        logger.info("[ObservatoryModel] PIPELINE COMPLETE")
        logger.info(f"Report: {self.report}")
        logger.info("=" * 60)
        return self.report

    # ─────────────────────────────────────────────────────────
    # Callback appelé par chaque agent à la fin de son step()
    # ─────────────────────────────────────────────────────────
    def on_agent_done(self, agent_name: str, result: Dict):
        """Les agents appellent cette méthode pour reporter leur résultat."""
        self.report[agent_name] = result
        self._pipeline_done[agent_name] = True
        logger.debug(f"[ObservatoryModel] ← {agent_name} done: {result}")
