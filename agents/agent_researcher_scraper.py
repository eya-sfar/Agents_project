"""
agents/agent_researcher_scraper.py

Automatically discovers researcher profiles using:
  ► OpenAlex  (primary)  — free, no API key, 250M+ works
  ► DBLP      (fallback) — free, no API key, CS-focused

NO manual name input needed. Just configure:
  - country_code / country name  (e.g. "TN", "FR", "Tunisia", "France")
  - institution_name             (e.g. "Université de Tunis El Manar")
  - OR a research topic/keyword  (e.g. "machine learning")

OpenAlex docs: https://docs.openalex.org/api-entities/authors

FIXED:
  - correct OpenAlex filter: last_known_institution.country_code:XX
  - removed invalid `select` fields (summary_stats, ids) that caused HTTP 400
  - accept full country names (France, Tunisia…) not just ISO codes
"""
import time
from typing import List, Dict, Optional

import requests

from agents.base_agent import BaseAgent
from database.connection import get_session
from database.repositories import ResearcherRepository
from config.settings import settings
from utils.logger import logger
from utils.helpers import retry, normalize_name, safe_int


OPENALEX_BASE = "https://api.openalex.org"
HEADERS = {"User-Agent": "UniversityObservatory/1.0 (mailto:observatory@university.edu)"}

# Full country name → ISO 2-letter code mapping (extend as needed)
COUNTRY_NAME_MAP = {
    "france": "FR", "tunisia": "TN", "algeria": "DZ", "morocco": "MA",
    "egypt": "EG", "germany": "DE", "italy": "IT", "spain": "ES",
    "usa": "US", "united states": "US", "uk": "GB", "united kingdom": "GB",
    "canada": "CA", "australia": "AU", "china": "CN", "japan": "JP",
    "brazil": "BR", "india": "IN", "saudi arabia": "SA", "qatar": "QA",
    "turkey": "TR", "netherlands": "NL", "belgium": "BE", "sweden": "SE",
    "portugal": "PT", "switzerland": "CH", "poland": "PL",
}


def resolve_country_code(raw: str) -> str:
    """Convert any country input (ISO or full name) to 2-letter ISO code."""
    raw = raw.strip()
    if len(raw) == 2:
        return raw.upper()
    return COUNTRY_NAME_MAP.get(raw.lower(), raw[:2].upper())


class AgentResearcherScraper(BaseAgent):

    def __init__(self):
        super().__init__("AgentResearcherScraper")

    # ─────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────
    def run(
        self,
        country_code: str = None,
        institution_name: str = None,
        topic: str = None,
        seed_names: List[str] = None,
        lab_id: str = None,
        max_authors: int = None,
    ) -> Dict:
        """
        Automatically discover researchers. All parameters are OPTIONAL.

        Priority:
          1. institution_name → OpenAlex institution search
          2. country_code     → all researchers from that country
          3. topic            → researchers who publish on this topic
          4. seed_names       → name-by-name DBLP lookup (fallback)
        """
        max_authors = max_authors or settings.agents.MAX_RESEARCHERS
        created, updated = 0, 0
        profiles: List[Dict] = []

        # ── Strategy 1: by institution ────────────────────────
        if institution_name:
            logger.info(f"[{self.name}] Searching by institution: {institution_name}")
            inst_id = self._resolve_institution(institution_name)
            if inst_id:
                profiles = self._paginate_authors(
                    filter_str=f"last_known_institution.id:{inst_id}",
                    max_n=max_authors,
                )
            else:
                logger.warning(f"[{self.name}] Institution not found: {institution_name}")

        # ── Strategy 2: by country ────────────────────────────
        if not profiles and country_code:
            iso = resolve_country_code(country_code)
            logger.info(f"[{self.name}] Searching by country: {country_code} → ISO={iso}")
            profiles = self._paginate_authors(
                filter_str=f"last_known_institution.country_code:{iso}",
                sort="cited_by_count:desc",
                max_n=max_authors,
            )

        # ── Strategy 3: by topic ──────────────────────────────
        if not profiles and topic:
            logger.info(f"[{self.name}] Searching by topic: {topic}")
            profiles = self._paginate_authors(
                search=topic,
                sort="cited_by_count:desc",
                max_n=max_authors,
            )

        # ── Strategy 4: seed names via OpenAlex / DBLP ────────
        if not profiles and seed_names:
            logger.info(f"[{self.name}] Falling back to seed names ({len(seed_names)} names)")
            for name in seed_names:
                p = self._lookup_by_name(name)
                if p:
                    profiles.append(p)
                time.sleep(0.3)

        if not profiles:
            logger.warning(
                f"[{self.name}] No profiles discovered. "
                "Check --country (ISO code like TN/FR), --institution, or --topic."
            )
            return {"created": 0, "updated": 0, "total": 0}

        logger.info(f"[{self.name}] Discovered {len(profiles)} profiles — saving to DB …")

        for profile in profiles:
            if lab_id:
                profile["lab_id"] = lab_id
            c, u = self._upsert_researcher(profile)
            created += c
            updated += u
            self._increment()

        return {"created": created, "updated": updated, "total": len(profiles)}

    # ─────────────────────────────────────────────────────────
    # Resolve institution name → OpenAlex ID
    # ─────────────────────────────────────────────────────────
    @retry(max_attempts=3, delay=2.0)
    def _resolve_institution(self, name: str) -> Optional[str]:
        resp = requests.get(
            f"{OPENALEX_BASE}/institutions",
            params={"search": name, "per-page": 1},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            inst = results[0]
            # Return just the short ID (e.g. I123456789)
            inst_id = inst["id"].split("/")[-1]
            logger.info(f"[{self.name}] Resolved: {inst['display_name']} → {inst_id}")
            return inst_id
        return None

    # ─────────────────────────────────────────────────────────
    # Core paginator — works for filter, search, or both
    # ─────────────────────────────────────────────────────────
    def _paginate_authors(
        self,
        filter_str: str = None,
        search: str = None,
        sort: str = "cited_by_count:desc",
        max_n: int = 200,
    ) -> List[Dict]:
        profiles = []
        page = 1
        per_page = min(50, max_n)

        while len(profiles) < max_n:
            # Only request fields that OpenAlex actually supports on /authors
            params = {
                "per-page": per_page,
                "page": page,
                "sort": sort,
                "select": "id,display_name,last_known_institution,works_count,cited_by_count,h_index,orcid",
            }
            if filter_str:
                params["filter"] = filter_str
            if search:
                params["search"] = search

            try:
                resp = requests.get(
                    f"{OPENALEX_BASE}/authors",
                    params=params,
                    headers=HEADERS,
                    timeout=20,
                )

                # Log actual URL on error for easier debugging
                if not resp.ok:
                    logger.error(
                        f"[{self.name}] OpenAlex HTTP {resp.status_code} — "
                        f"URL: {resp.url}\nBody: {resp.text[:300]}"
                    )
                    break

                data = resp.json()
                results = data.get("results", [])

                if not results:
                    logger.info(f"[{self.name}] No results on page {page} — stopping.")
                    break

                for author in results:
                    profiles.append(self._parse_author(author))

                total = data.get("meta", {}).get("count", 0)
                logger.info(
                    f"[{self.name}] Page {page}: +{len(results)} authors "
                    f"({len(profiles)}/{min(max_n, total)} collected, {total} available)"
                )

                if len(profiles) >= min(max_n, total) or len(results) < per_page:
                    break

                page += 1
                time.sleep(0.15)

            except Exception as e:
                logger.warning(f"[{self.name}] Error on page {page}: {e}")
                break

        return profiles[:max_n]

    # ─────────────────────────────────────────────────────────
    # Parse single OpenAlex author → DB dict
    # ─────────────────────────────────────────────────────────
    def _parse_author(self, author: Dict) -> Dict:
        inst = author.get("last_known_institution") or {}
        orcid_raw = author.get("orcid") or ""
        orcid = orcid_raw.replace("https://orcid.org/", "").strip() or None

        return {
            "name": author.get("display_name", "Unknown"),
            "department": inst.get("display_name"),
            "h_index": safe_int(author.get("h_index")),
            "total_citations": safe_int(author.get("cited_by_count")),
            "publications": safe_int(author.get("works_count")),
            "orcid": orcid,
            # Store full OpenAlex URL as profile_url for later pub fetching
            "profile_url": author.get("id"),
        }

    # ─────────────────────────────────────────────────────────
    # Name-based lookup (fallback for seed_names)
    # ─────────────────────────────────────────────────────────
    def _lookup_by_name(self, name: str) -> Optional[Dict]:
        # 1. Try OpenAlex
        try:
            resp = requests.get(
                f"{OPENALEX_BASE}/authors",
                params={"search": name, "per-page": 1,
                        "select": "id,display_name,last_known_institution,works_count,cited_by_count,h_index,orcid"},
                headers=HEADERS,
                timeout=10,
            )
            if resp.ok:
                results = resp.json().get("results", [])
                if results:
                    return self._parse_author(results[0])
        except Exception as e:
            logger.debug(f"OpenAlex name lookup failed for {name}: {e}")

        # 2. Try DBLP
        try:
            resp = requests.get(
                "https://dblp.org/search/author/api",
                params={"q": name, "format": "json", "h": 1},
                headers=HEADERS,
                timeout=10,
            )
            if resp.ok:
                hits = resp.json().get("result", {}).get("hits", {}).get("hit", [])
                if hits:
                    info = hits[0].get("info", {})
                    return {
                        "name": info.get("author", name),
                        "dblp_pid": info.get("pid"),
                        "profile_url": info.get("url"),
                    }
        except Exception as e:
            logger.debug(f"DBLP lookup failed for {name}: {e}")

        return None

    # ─────────────────────────────────────────────────────────
    # DB upsert
    # ─────────────────────────────────────────────────────────
    def _upsert_researcher(self, profile: Dict):
        created, updated = 0, 0
        with get_session() as session:
            repo = ResearcherRepository(session)

            existing = None
            if profile.get("orcid"):
                hits = repo.search(profile["name"])
                existing = next((r for r in hits if r.orcid == profile["orcid"]), None)

            if not existing:
                candidates = repo.search(normalize_name(profile["name"]))
                if candidates:
                    existing = candidates[0]

            if existing:
                repo.update(existing.researcher_id, profile)
                updated += 1
            else:
                repo.create(profile)
                created += 1

        return created, updated
