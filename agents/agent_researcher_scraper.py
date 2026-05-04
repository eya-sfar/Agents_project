"""
agents/agent_researcher_scraper.py

Logique identique au code original de l'étudiant :
  - is_valid_researcher() — filtre les noms invalides / keyword / bots
  - parse_author()        — extrait openalex_id, name, citations, h_index, expertise
  - fetch_page()          — appel OpenAlex /authors paginé
  - step()               — boucle pages → filtre → parse → sauvegarde DB

Adaptations :
  - Mesa 3.x  : super().__init__(model)  [plus de unique_id]
  - DB         : SQLAlchemy + ResearcherRepository (PostgreSQL)
  - Audit      : AgentRun log dans la DB
  - Filtre URL : last_known_institutions.type:education  (comme ton code)
"""
import mesa
import requests
from datetime import datetime
from typing import List, Dict, Optional

from database.connection import get_session
from database.repositories import ResearcherRepository
from database.models import AgentRun
from utils.logger import logger


OPENALEX_BASE = "https://api.openalex.org"
HEADERS = {"User-Agent": "ResearchMAS/1.0"}


class AgentResearcherScraper(mesa.Agent):

    # Noms qui ressemblent à des topics, pas des personnes
    BLACKLISTED_NAMES = {
        "machine learning", "deep learning", "artificial intelligence",
        "neural network", "data science", "computer vision",
        "natural language processing", "reinforcement learning",
        "big data", "internet of things", "cloud computing",
    }

    def __init__(self, model: mesa.Model, keyword: str = "machine learning", max_pages: int = 3):
        # Mesa 3.x — plus de unique_id
        super().__init__(model)
        self.keyword   = keyword
        self.max_pages = max_pages
        self.collected: List[Dict] = []
        self.run_id: Optional[str] = None

        # Paramètres injectés par ObservatoryModel avant step()
        self.country_code:     Optional[str] = None
        self.institution_name: Optional[str] = None
        self.topic:            Optional[str] = None
        self.seed_names:       List[str]     = []
        self.lab_id:           Optional[str] = None
        self.max_authors:      int           = 200

    # ─────────────────────────────────────────────────────────
    # VALIDATION — identique à ton code original
    # ─────────────────────────────────────────────────────────
    def is_valid_researcher(self, author: dict) -> bool:
        name = author.get("display_name", "").strip()

        # Doit avoir au moins prénom + nom
        if not name or len(name.split()) < 2:
            return False

        # Pas de chiffres dans le nom
        if any(char.isdigit() for char in name):
            return False

        # Le keyword ne doit pas être dans le nom
        if self.keyword.lower() in name.lower():
            return False

        # Blacklist des noms qui sont des topics
        if name.lower() in self.BLACKLISTED_NAMES:
            return False

        # Filtre les comptes institutionnels (trop de publications)
        if author.get("works_count", 0) > 5000:
            return False

        return True

    # ─────────────────────────────────────────────────────────
    # PARSE — identique à ton code original
    # ─────────────────────────────────────────────────────────
    def parse_author(self, author: dict) -> dict:
        # x_concepts contient les domaines de recherche avec un score
        concepts = author.get("x_concepts", [])
        expertise = ", ".join(
            c["display_name"]
            for c in concepts[:5]
            if c.get("score", 0) > 0.1
        )

        return {
            "openalex_id": author.get("id", ""),
            "name":        author.get("display_name", "Unknown"),
            "citations":   author.get("cited_by_count", 0),
            "h_index":     author.get("summary_stats", {}).get("h_index", 0),
            "works_count": author.get("works_count", 0),
            "expertise":   expertise or self.keyword,
        }

    # ─────────────────────────────────────────────────────────
    # FETCH PAGE — même structure que ton code original
    # ─────────────────────────────────────────────────────────
    def fetch_page(self, page: int) -> list:
        try:
            # Construire le filtre selon les paramètres disponibles
            if self.country_code:
                filter_str = f"last_known_institutions.country_code:{self.country_code.upper()},last_known_institutions.type:education"
            elif self.institution_name:
                inst_id = self._resolve_institution(self.institution_name)
                filter_str = f"last_known_institutions.id:{inst_id}" if inst_id else "last_known_institutions.type:education"
            else:
                # Défaut — ton filtre original
                filter_str = "last_known_institutions.type:education"

            url = (
                f"{OPENALEX_BASE}/authors"
                f"?filter={filter_str}"
                f"&sort=cited_by_count:desc"
                f"&per-page=25&page={page}"
            )
            response = requests.get(url, timeout=15, headers=HEADERS)
            response.raise_for_status()
            results = response.json().get("results", [])
            return results

        except requests.RequestException as e:
            print(f"[AgentResearcherScraper] Warning: page {page} failed — {e}")
            return []

    # ─────────────────────────────────────────────────────────
    # MESA STEP — même logique que ton code original + sauvegarde DB
    # ─────────────────────────────────────────────────────────
    def step(self):
        self._log_start()
        self.collected = []

        for page in range(1, self.max_pages + 1):
            results = self.fetch_page(page)
            if not results:
                break

            for author in results:
                if self.is_valid_researcher(author):
                    researcher_data = self.parse_author(author)
                    self.collected.append(researcher_data)
                    self._save_researcher(researcher_data)

        print(f"[AgentResearcherScraper] Collected and saved {len(self.collected)} researchers for '{self.keyword}'")
        logger.info(f"[AgentResearcherScraper] {len(self.collected)} researchers saved")
        self._log_finish(records=len(self.collected))

        # Notifier le modèle Mesa
        self.model.on_agent_done("AgentResearcherScraper", {
            "collected": len(self.collected),
            "keyword":   self.keyword,
        })

    # ─────────────────────────────────────────────────────────
    # SAVE — adapté pour notre DB PostgreSQL
    # (ton code utilisait session.add directement, on passe par le repo)
    # ─────────────────────────────────────────────────────────
    def _save_researcher(self, data: dict):
        """Upsert un chercheur en DB (comme ton session.add + commit)."""
        with get_session() as session:
            repo = ResearcherRepository(session)

            # Chercher par openalex_id stocké dans profile_url
            existing = None
            candidates = repo.search(data["name"])
            for r in candidates:
                if r.profile_url == data["openalex_id"]:
                    existing = r
                    break

            db_record = {
                "name":            data["name"],
                "h_index":         data["h_index"],
                "total_citations": data["citations"],
                "publications":    data["works_count"],
                "profile_url":     data["openalex_id"],   # stocke l'ID OpenAlex
                "department":      data["expertise"][:255] if data["expertise"] else "Unknown",
                "lab_id":          self.lab_id,
            }

            if existing:
                repo.update(existing.researcher_id, db_record)
            else:
                repo.create(db_record)

    # ─────────────────────────────────────────────────────────
    # Résolution institution → OpenAlex ID
    # ─────────────────────────────────────────────────────────
    def _resolve_institution(self, name: str) -> Optional[str]:
        try:
            resp = requests.get(
                f"{OPENALEX_BASE}/institutions",
                params={"search": name, "per-page": 1},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                return results[0]["id"].split("/")[-1]
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────
    # Audit log DB
    # ─────────────────────────────────────────────────────────
    def _log_start(self):
        with get_session() as session:
            run = AgentRun(agent_name="AgentResearcherScraper", status="started")
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
