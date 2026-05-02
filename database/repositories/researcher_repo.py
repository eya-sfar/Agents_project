"""
database/repositories/researcher_repo.py
Data-access layer for Researcher records.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.models import Researcher, Expertise
from utils.logger import logger


class ResearcherRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Create ────────────────────────────────────────────────
    def create(self, data: dict) -> Researcher:
        researcher = Researcher(**data)
        self.session.add(researcher)
        self.session.flush()
        logger.debug(f"Created researcher: {researcher.name}")
        return researcher

    # ── Read ──────────────────────────────────────────────────
    def get_by_id(self, researcher_id: str) -> Optional[Researcher]:
        return self.session.query(Researcher).filter_by(researcher_id=researcher_id).first()

    def get_by_scholar_id(self, scholar_id: str) -> Optional[Researcher]:
        return self.session.query(Researcher).filter_by(google_scholar_id=scholar_id).first()

    def get_all(self, active_only: bool = True) -> List[Researcher]:
        q = self.session.query(Researcher)
        if active_only:
            q = q.filter_by(is_active=True)
        return q.all()

    def search(self, query: str) -> List[Researcher]:
        pattern = f"%{query}%"
        return (
            self.session.query(Researcher)
            .filter(
                or_(
                    Researcher.name.ilike(pattern),
                    Researcher.department.ilike(pattern),
                )
            )
            .all()
        )

    def get_by_lab(self, lab_id: str) -> List[Researcher]:
        return self.session.query(Researcher).filter_by(lab_id=lab_id).all()

    def count(self) -> int:
        return self.session.query(Researcher).count()

    def get_top_by_h_index(self, limit: int = 10) -> List[Researcher]:
        return (
            self.session.query(Researcher)
            .order_by(Researcher.h_index.desc())
            .limit(limit)
            .all()
        )

    # ── Update ────────────────────────────────────────────────
    def update(self, researcher_id: str, data: dict) -> Optional[Researcher]:
        researcher = self.get_by_id(researcher_id)
        if not researcher:
            return None
        for key, value in data.items():
            setattr(researcher, key, value)
        self.session.flush()
        return researcher

    # ── Expertise helpers ─────────────────────────────────────
    def upsert_expertise(self, researcher_id: str, area: str, keywords: list, score: float = 1.0, source: str = "inferred"):
        existing = (
            self.session.query(Expertise)
            .filter_by(researcher_id=researcher_id, area=area)
            .first()
        )
        if existing:
            existing.keywords = keywords
            existing.score = score
        else:
            exp = Expertise(
                researcher_id=researcher_id,
                area=area,
                keywords=keywords,
                score=score,
                source=source,
            )
            self.session.add(exp)
        self.session.flush()

    def get_expertise(self, researcher_id: str) -> List[Expertise]:
        return self.session.query(Expertise).filter_by(researcher_id=researcher_id).all()

    # ── Delete ────────────────────────────────────────────────
    def delete(self, researcher_id: str) -> bool:
        researcher = self.get_by_id(researcher_id)
        if not researcher:
            return False
        self.session.delete(researcher)
        return True