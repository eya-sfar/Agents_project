"""
agents/agent_lab_scraper.py

Discovers and stores laboratory information.
Sources:
  - CORDIS (EU research project database) — free, no key
  - Manual seed data (JSON / dict list provided by coordinator)
  - Generic university website scraping
"""
import time
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

from agents.base_agent import BaseAgent
from database.connection import get_session
from database.repositories import LabRepository
from config.settings import settings
from utils.logger import logger
from utils.helpers import retry


class AgentLabScraper(BaseAgent):

    CORDIS_API = "https://cordis.europa.eu/api/projects"

    def __init__(self):
        super().__init__("AgentLabScraper")

    # ── Main ──────────────────────────────────────────────────
    def run(self, seed_labs: List[Dict] = None, university_url: str = None) -> Dict:
        """
        Args:
            seed_labs:      List of dicts with lab info to insert directly.
            university_url: URL of a university research page to scrape.
        """
        created = 0
        seed_labs = seed_labs or []

        # 1. Insert seed / manual labs
        for lab_data in seed_labs:
            c = self._upsert_lab(lab_data)
            created += c
            self._increment()

        # 2. Scrape university website
        if university_url:
            labs = self._scrape_university_page(university_url)
            for lab_data in labs:
                c = self._upsert_lab(lab_data)
                created += c
                self._increment()
                time.sleep(settings.agents.SCRAPE_DELAY_SECONDS)

        return {"labs_created": created}

    # ── Scraping ──────────────────────────────────────────────
    @retry(max_attempts=3, delay=2.0)
    def _scrape_university_page(self, url: str) -> List[Dict]:
        """Generic scraper: finds <a> tags that look like lab names."""
        headers = {"User-Agent": "Mozilla/5.0 (Research Observatory Bot)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        labs = []

        # Heuristic: look for headings or list items that contain "lab", "laboratory", "unit"
        keywords = ["lab", "laboratory", "unit", "centre", "center", "group", "team"]
        for tag in soup.find_all(["h2", "h3", "h4", "li", "a"]):
            text = tag.get_text(strip=True)
            low = text.lower()
            if any(kw in low for kw in keywords) and 5 < len(text) < 200:
                href = tag.get("href", "") if tag.name == "a" else ""
                labs.append({
                    "name": text[:255],
                    "website": href if href.startswith("http") else None,
                })

        logger.info(f"[{self.name}] Found {len(labs)} potential labs on {url}")
        return labs[:50]  # cap at 50

    # ── DB upsert ─────────────────────────────────────────────
    def _upsert_lab(self, data: Dict) -> int:
        with get_session() as session:
            repo = LabRepository(session)
            existing = repo.search(data.get("name", ""))
            if existing:
                repo.update(existing[0].lab_id, data)
                return 0
            repo.create(data)
            return 1
