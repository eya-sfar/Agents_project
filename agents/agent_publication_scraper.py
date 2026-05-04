"""
agents/agent_publication_scraper.py

Version corrigée :
✔ Filtrage des publications par chercheur (author.id)
✔ Structure originale conservée
✔ Intégration Mesa + PostgreSQL inchangée
"""

import mesa
import requests
from datetime import datetime
from typing import List, Dict, Optional

from database.connection import get_session
from database.repositories import ResearcherRepository, PublicationRepository
from database.models import AgentRun
from utils.logger import logger


OPENALEX_BASE = "https://api.openalex.org"
HEADERS = {"User-Agent": "ResearchMAS/1.0"}


class AgentPublicationScraper(mesa.Agent):

    def __init__(self, model: mesa.Model, max_pages: int = 5):
        super().__init__(model)

        self.max_pages = max_pages
        self.collected: List[Dict] = []
        self.run_id: Optional[str] = None

        # Injecté par ObservatoryModel
        self.researcher_ids: Optional[List[str]] = None
        self.max_per_author: int = 50

    # ─────────────────────────────────────────────────────────
    # FETCH PAGE — corrigé (filtrage par auteur)
    # ─────────────────────────────────────────────────────────
    def fetch_page(self, page: int, author_id: str) -> list:
        try:
            url = (
                f"{OPENALEX_BASE}/works"
                f"?filter=author.id:{author_id},type:article"
                f"&sort=cited_by_count:desc"
                f"&per-page=25&page={page}"
            )

            response = requests.get(url, timeout=15, headers=HEADERS)
            response.raise_for_status()

            return response.json().get("results", [])

        except requests.RequestException as e:
            logger.warning(f"[AgentPublicationScraper] Page {page} failed — {e}")
            return []

    # ─────────────────────────────────────────────────────────
    # PARSE WORK — inchangé
    # ─────────────────────────────────────────────────────────
    def parse_work(self, work: dict) -> dict:
        authorships = work.get("authorships", [])

        authors = ", ".join(
            a.get("author", {}).get("display_name", "Unknown")
            for a in authorships[:5]
        )

        first_author_id = None
        if authorships:
            first_author_id = authorships[0].get("author", {}).get("id", None)

        # Reconstruction abstract
        abstract = ""
        inv = work.get("abstract_inverted_index") or {}
        if inv:
            pos_word = {}
            for word, positions in inv.items():
                for pos in positions:
                    pos_word[pos] = word
            abstract = " ".join(pos_word[i] for i in sorted(pos_word))[:2000]

        location = work.get("primary_location") or {}
        source = location.get("source") or {}

        doi_raw = work.get("doi") or ""
        doi = doi_raw.replace("https://doi.org/", "").strip() or None

        return {
            "title": work.get("title", "Unknown"),
            "year": work.get("publication_year", 0),
            "citations": work.get("cited_by_count", 0),
            "authors": authors,
            "first_author_openalex_id": first_author_id,
            "abstract": abstract or None,
            "venue": source.get("display_name"),
            "doi": doi,
            "url": work.get("id"),
            "pub_type": work.get("type", "article"),
        }

    # ─────────────────────────────────────────────────────────
    # STEP — corrigé (boucle par chercheur)
    # ─────────────────────────────────────────────────────────
    def step(self):
        self._log_start()
        self.collected = []

        with get_session() as session:
            r_repo = ResearcherRepository(session)
            researchers = r_repo.get_all()

            for researcher in researchers:
                author_id = researcher.profile_url  # OpenAlex ID

                if not author_id:
                    continue

                count = 0

                for page in range(1, self.max_pages + 1):
                    results = self.fetch_page(page, author_id)

                    if not results:
                        break

                    for work in results:
                        if work.get("title"):
                            parsed = self.parse_work(work)
                            self.collected.append(parsed)
                            self._save_publication(parsed)

                            count += 1
                            if count >= self.max_per_author:
                                break

                    if count >= self.max_per_author:
                        break

        logger.info(f"[AgentPublicationScraper] {len(self.collected)} publications saved")

        self._log_finish(records=len(self.collected))

        self.model.on_agent_done("AgentPublicationScraper", {
            "collected": len(self.collected),
        })

    # ─────────────────────────────────────────────────────────
    # SAVE — inchangé (avec petite amélioration)
    # ─────────────────────────────────────────────────────────
    def _save_publication(self, data: dict):
        with get_session() as session:
            pub_repo = PublicationRepository(session)

            # Déduplication robuste
            doi = data.get("doi")
            if doi and pub_repo.get_by_doi(doi):
                return

            # Trouver le chercheur via OpenAlex ID
            author_ids = []
            first_openalex = data.get("first_author_openalex_id")

            if first_openalex:
                result = session.execute(
                    __import__("sqlalchemy").text(
                        "SELECT researcher_id FROM researchers WHERE profile_url = :oid LIMIT 1"
                    ),
                    {"oid": first_openalex},
                ).fetchone()

                if result:
                    author_ids = [str(result[0])]

            db_pub = {
                "title": data["title"],
                "abstract": data.get("abstract"),
                "year": data.get("year") or 0,
                "citations": data.get("citations") or 0,
                "venue": data.get("venue"),
                "doi": doi,
                "url": data.get("url"),
                "pub_type": data.get("pub_type", "article"),
            }

            pub_repo.create(db_pub, author_ids=author_ids)

    # ─────────────────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────────────────
    def _log_start(self):
        with get_session() as session:
            run = AgentRun(agent_name="AgentPublicationScraper", status="started")
            session.add(run)
            session.flush()
            self.run_id = run.run_id

    def _log_finish(self, records: int = 0, error: str = None):
        with get_session() as session:
            run = session.query(AgentRun).filter_by(run_id=self.run_id).first()

            if run:
                run.status = "completed" if not error else "failed"
                run.records_processed = records
                run.error_message = error
                run.finished_at = datetime.utcnow()