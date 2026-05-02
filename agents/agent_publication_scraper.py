"""
agents/agent_publication_scraper.py

Fetches publications for known researchers via OpenAlex (primary).
Fallback: DBLP (CS-focused, no key).

FIXED:
  - Use correct OpenAlex /works select fields (no invalid fields)
  - Resolve author OpenAlex ID from profile_url stored in DB
  - Reconstruct abstract from inverted index
  - Better per-author fetch with pagination
"""
import time
from typing import List, Dict, Optional

import requests

from agents.base_agent import BaseAgent
from database.connection import get_session
from database.repositories import ResearcherRepository, PublicationRepository
from config.settings import settings
from utils.logger import logger
from utils.helpers import retry, safe_int

OPENALEX_BASE = "https://api.openalex.org"
HEADERS = {"User-Agent": "UniversityObservatory/1.0 (mailto:observatory@university.edu)"}


class AgentPublicationScraper(BaseAgent):

    def __init__(self):
        super().__init__("AgentPublicationScraper")

    # ─────────────────────────────────────────────────────────
    # Main
    # ─────────────────────────────────────────────────────────
    def run(self, researcher_ids: List[str] = None, max_per_author: int = 50) -> Dict:
        with get_session() as session:
            repo = ResearcherRepository(session)
            if researcher_ids:
                researchers = [r for rid in researcher_ids if (r := repo.get_by_id(rid))]
            else:
                researchers = repo.get_all(active_only=True)

        total_new = 0
        for researcher in researchers:
            logger.info(f"[{self.name}] Fetching pubs for: {researcher.name}")
            pubs = self._fetch_for_researcher(researcher, max_per_author)
            new = self._store(pubs, researcher.researcher_id)
            total_new += new
            self._increment(new)
            time.sleep(0.2)

        return {"total_new_publications": total_new}

    # ─────────────────────────────────────────────────────────
    # Fetch pipeline per researcher
    # ─────────────────────────────────────────────────────────
    def _fetch_for_researcher(self, researcher, max_n: int) -> List[Dict]:
        # Extract OpenAlex author ID from profile_url (e.g. https://openalex.org/A12345)
        openalex_id = None
        if researcher.profile_url and "openalex.org/" in researcher.profile_url:
            openalex_id = researcher.profile_url.rstrip("/").split("/")[-1]

        # Also try ORCID lookup
        if not openalex_id and researcher.orcid:
            openalex_id = self._resolve_id_by_orcid(researcher.orcid)

        # Try name search if still no ID
        if not openalex_id:
            openalex_id = self._resolve_id_by_name(researcher.name)

        if openalex_id:
            pubs = self._fetch_works_by_author(openalex_id, max_n)
            if pubs:
                logger.info(f"[{self.name}] Got {len(pubs)} pubs via OpenAlex for {researcher.name}")
                return pubs

        # Fallback: DBLP
        if researcher.dblp_pid:
            pubs = self._fetch_dblp(researcher.dblp_pid, max_n)
            if pubs:
                logger.info(f"[{self.name}] Got {len(pubs)} pubs via DBLP for {researcher.name}")
                return pubs

        logger.debug(f"[{self.name}] No publications found for: {researcher.name}")
        return []

    # ─────────────────────────────────────────────────────────
    # Resolve author ID from ORCID
    # ─────────────────────────────────────────────────────────
    def _resolve_id_by_orcid(self, orcid: str) -> Optional[str]:
        try:
            resp = requests.get(
                f"{OPENALEX_BASE}/authors",
                params={"filter": f"orcid:{orcid}", "per-page": 1,
                        "select": "id"},
                headers=HEADERS, timeout=10,
            )
            if resp.ok:
                results = resp.json().get("results", [])
                if results:
                    return results[0]["id"].split("/")[-1]
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────
    # Resolve author ID from name
    # ─────────────────────────────────────────────────────────
    def _resolve_id_by_name(self, name: str) -> Optional[str]:
        try:
            resp = requests.get(
                f"{OPENALEX_BASE}/authors",
                params={"search": name, "per-page": 1, "select": "id"},
                headers=HEADERS, timeout=10,
            )
            if resp.ok:
                results = resp.json().get("results", [])
                if results:
                    return results[0]["id"].split("/")[-1]
        except Exception as e:
            logger.debug(f"Name resolve failed for {name}: {e}")
        return None

    # ─────────────────────────────────────────────────────────
    # Fetch works by OpenAlex author ID
    # ─────────────────────────────────────────────────────────
    @retry(max_attempts=3, delay=2.0)
    def _fetch_works_by_author(self, author_id: str, max_n: int) -> List[Dict]:
        pubs = []
        page = 1
        per_page = min(50, max_n)

        while len(pubs) < max_n:
            resp = requests.get(
                f"{OPENALEX_BASE}/works",
                params={
                    "filter": f"authorships.author.id:{author_id}",
                    "sort": "cited_by_count:desc",
                    "per-page": per_page,
                    "page": page,
                    # Only valid /works fields
                    "select": "id,title,abstract_inverted_index,publication_year,"
                              "cited_by_count,primary_location,type,doi",
                },
                headers=HEADERS,
                timeout=20,
            )

            if not resp.ok:
                logger.warning(
                    f"[{self.name}] OpenAlex /works HTTP {resp.status_code}: {resp.text[:200]}"
                )
                break

            results = resp.json().get("results", [])
            if not results:
                break

            for work in results:
                pubs.append(self._parse_work(work))

            if len(results) < per_page:
                break
            page += 1
            time.sleep(0.1)

        return pubs[:max_n]

    # ─────────────────────────────────────────────────────────
    # Parse one OpenAlex work
    # ─────────────────────────────────────────────────────────
    def _parse_work(self, work: Dict) -> Dict:
        # Reconstruct abstract from inverted index
        abstract = ""
        inv = work.get("abstract_inverted_index") or {}
        if inv:
            pos_word = {}
            for word, positions in inv.items():
                for pos in positions:
                    pos_word[pos] = word
            abstract = " ".join(pos_word[i] for i in sorted(pos_word))[:2000]

        location = work.get("primary_location") or {}
        source   = location.get("source") or {}

        doi_raw = work.get("doi") or ""
        doi = doi_raw.replace("https://doi.org/", "").strip() or None

        return {
            "title":     work.get("title") or "",
            "abstract":  abstract or None,
            "year":      safe_int(work.get("publication_year")),
            "citations": safe_int(work.get("cited_by_count")),
            "venue":     source.get("display_name"),
            "doi":       doi,
            "url":       work.get("id"),
            "pub_type":  work.get("type", "article"),
        }

    # ─────────────────────────────────────────────────────────
    # DBLP fallback
    # ─────────────────────────────────────────────────────────
    @retry(max_attempts=2, delay=2.0)
    def _fetch_dblp(self, pid: str, max_n: int) -> List[Dict]:
        try:
            resp = requests.get(
                f"https://dblp.org/pid/{pid}.json",
                headers=HEADERS, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            result = []
            for entry in data.get("result", {}).get("hits", {}).get("hit", [])[:max_n]:
                info = entry.get("info", {})
                result.append({
                    "title":    info.get("title", ""),
                    "year":     safe_int(info.get("year")),
                    "venue":    info.get("venue"),
                    "url":      info.get("url"),
                    "pub_type": info.get("type", "conference"),
                    "citations": 0,
                })
            return result
        except Exception as e:
            logger.debug(f"DBLP fetch failed for pid={pid}: {e}")
            return []

    # ─────────────────────────────────────────────────────────
    # Store to DB (dedup by DOI or title)
    # ─────────────────────────────────────────────────────────
    def _store(self, pubs: List[Dict], researcher_id: str) -> int:
        new_count = 0
        with get_session() as session:
            pub_repo = PublicationRepository(session)
            for pub in pubs:
                if not pub.get("title"):
                    continue
                if pub.get("doi") and pub_repo.get_by_doi(pub["doi"]):
                    continue
                pub_repo.create(pub, author_ids=[researcher_id])
                new_count += 1
        return new_count
