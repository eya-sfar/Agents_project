"""
agents/agent_lab_scraper.py

Logique identique au code original de l'étudiant :
  - parse_institution() — extrait name, department, university, country
  - fetch_page()        — appel OpenAlex /institutions paginé (filter=type:education)
  - step()              — boucle pages → parse → sauvegarde DB

Adaptations :
  - Mesa 3.x : super().__init__(model)
  - DB        : LabRepository (PostgreSQL)
  - Extra     : support seed_labs + scraping site web
"""
import mesa
import requests
from datetime import datetime
from typing import List, Dict, Optional

from database.connection import get_session
from database.repositories import LabRepository
from database.models import AgentRun
from utils.logger import logger


OPENALEX_BASE = "https://api.openalex.org"
HEADERS = {"User-Agent": "ResearchMAS/1.0"}


class AgentLabScraper(mesa.Agent):

    def __init__(self, model: mesa.Model, max_pages: int = 5):
        # Mesa 3.x — plus de unique_id
        super().__init__(model)
        self.max_pages = max_pages
        self.collected: List[Dict] = []
        self.run_id: Optional[str] = None

        # Injectés par ObservatoryModel avant step()
        self.seed_labs:      List[Dict]    = []
        self.university_url: Optional[str] = None
        self.country_code:   Optional[str] = None

    # ─────────────────────────────────────────────────────────
    # FETCH PAGE — identique à ton code original
    # ─────────────────────────────────────────────────────────
    def fetch_page(self, page: int) -> list:
        try:
            # Filtre de base : institutions éducatives
            filter_str = "type:education"
            if self.country_code:
                filter_str += f",country_code:{self.country_code.upper()}"

            url = (
                f"{OPENALEX_BASE}/institutions"
                f"?filter={filter_str}"
                f"&sort=cited_by_count:desc"
                f"&per-page=25&page={page}"
            )
            response = requests.get(url, timeout=15, headers=HEADERS)
            response.raise_for_status()
            results = response.json().get("results", [])
            return results

        except requests.RequestException as e:
            print(f"[AgentLabScraper] Warning: page {page} failed — {e}")
            return []

    # ─────────────────────────────────────────────────────────
    # PARSE INSTITUTION — identique à ton code original
    # ─────────────────────────────────────────────────────────
    def parse_institution(self, inst: dict) -> dict:
        geo = inst.get("geo", {})
        return {
            "name":        inst.get("display_name", "Unknown"),
            "department":  inst.get("type", "Unknown"),
            "university":  inst.get("display_name", "Unknown"),
            "country":     geo.get("country", "Unknown"),
            # Champs supplémentaires pour la DB
            "website":     inst.get("homepage_url"),
            "description": f"Works: {inst.get('works_count', 0)} | OpenAlex: {inst.get('id', '')}",
        }

    # ─────────────────────────────────────────────────────────
    # MESA STEP — même logique que ton code original + sauvegarde DB
    # ─────────────────────────────────────────────────────────
    def step(self):
        self._log_start()
        self.collected = []

        # 1. Seed labs manuels (passés par le coordinateur)
        for lab in self.seed_labs:
            if lab.get("name"):
                self.collected.append(lab)
                self._save_lab(lab)

        # 2. OpenAlex /institutions — même boucle que ton code original
        for page in range(1, self.max_pages + 1):
            results = self.fetch_page(page)
            if not results:
                break

            for inst in results:
                if inst.get("display_name"):
                    parsed = self.parse_institution(inst)
                    self.collected.append(parsed)
                    self._save_lab(parsed)

        print(f"[AgentLabScraper] Collected {len(self.collected)} labs")
        logger.info(f"[AgentLabScraper] {len(self.collected)} labs saved")
        self._log_finish(records=len(self.collected))

        self.model.on_agent_done("AgentLabScraper", {
            "collected": len(self.collected),
        })

    # ─────────────────────────────────────────────────────────
    # SAVE — sauvegarde en DB
    # ─────────────────────────────────────────────────────────
    def _save_lab(self, data: dict):
        """Upsert un lab en DB."""
        name = (data.get("name") or "").strip()
        if not name or name == "Unknown":
            return

        with get_session() as session:
            repo = LabRepository(session)
            existing = repo.search(name)
            if existing:
                repo.update(existing[0].lab_id, data)
            else:
                repo.create(data)

    # ─────────────────────────────────────────────────────────
    # Audit log DB
    # ─────────────────────────────────────────────────────────
    def _log_start(self):
        with get_session() as session:
            run = AgentRun(agent_name="AgentLabScraper", status="started")
            session.add(run)
            session.flush()
            self.run_id = run.run_id

    def _log_finish(self, records: int = 0, error: str = None):
        with get_session() as session:
            run = session.query(AgentRun).filter_by(run_id=self.run_id).first()
            if run:
                run.status            = "completed" if not error else "failed"
                run.records_processed = records
                run.error_message     = error
                run.finished_at       = datetime.utcnow()
