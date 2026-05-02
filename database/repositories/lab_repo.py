"""
database/repositories/lab_repo.py
Data-access layer for Lab records.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Lab
from utils.logger import logger


class LabRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: dict) -> Lab:
        lab = Lab(**data)
        self.session.add(lab)
        self.session.flush()
        logger.debug(f"Created lab: {lab.name}")
        return lab

    def get_by_id(self, lab_id: str) -> Optional[Lab]:
        return self.session.query(Lab).filter_by(lab_id=lab_id).first()

    def get_all(self) -> List[Lab]:
        return self.session.query(Lab).all()

    def search(self, query: str) -> List[Lab]:
        pattern = f"%{query}%"
        return self.session.query(Lab).filter(Lab.name.ilike(pattern)).all()

    def update(self, lab_id: str, data: dict) -> Optional[Lab]:
        lab = self.get_by_id(lab_id)
        if not lab:
            return None
        for key, value in data.items():
            setattr(lab, key, value)
        self.session.flush()
        return lab

    def update_researcher_count(self, lab_id: str):
        from database.models import Researcher
        count = self.session.query(Researcher).filter_by(lab_id=lab_id).count()
        self.update(lab_id, {"num_researchers": count})

    def delete(self, lab_id: str) -> bool:
        lab = self.get_by_id(lab_id)
        if not lab:
            return False
        self.session.delete(lab)
        return True