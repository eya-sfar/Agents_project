"""
database/repositories/publication_repo.py
Data-access layer for Publication records.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Publication, PublicationAuthor
from utils.logger import logger


class PublicationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: dict, author_ids: List[str] = None) -> Publication:
        pub = Publication(**data)
        self.session.add(pub)
        self.session.flush()

        for order, rid in enumerate(author_ids or [], start=1):
            link = PublicationAuthor(
                publication_id=pub.publication_id,
                researcher_id=rid,
                author_order=order,
            )
            self.session.add(link)

        self.session.flush()
        logger.debug(f"Created publication: {pub.title[:60]}")
        return pub

    def get_by_id(self, pub_id: str) -> Optional[Publication]:
        return self.session.query(Publication).filter_by(publication_id=pub_id).first()

    def get_by_doi(self, doi: str) -> Optional[Publication]:
        return self.session.query(Publication).filter_by(doi=doi).first()

    def get_by_researcher(self, researcher_id: str) -> List[Publication]:
        return (
            self.session.query(Publication)
            .join(PublicationAuthor)
            .filter(PublicationAuthor.researcher_id == researcher_id)
            .order_by(Publication.year.desc())
            .all()
        )

    def get_all(self, limit: int = 200) -> List[Publication]:
        return self.session.query(Publication).order_by(Publication.year.desc()).limit(limit).all()

    def get_top_cited(self, limit: int = 20) -> List[Publication]:
        return (
            self.session.query(Publication)
            .order_by(Publication.citations.desc())
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.session.query(Publication).count()