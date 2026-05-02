"""
database/repositories/cluster_repo.py
Data-access layer for Cluster records.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Cluster, ClusterMember, Collaboration
from utils.logger import logger


class ClusterRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Clusters ──────────────────────────────────────────────
    def create_cluster(self, data: dict) -> Cluster:
        cluster = Cluster(**data)
        self.session.add(cluster)
        self.session.flush()
        return cluster

    def add_member(self, cluster_id: str, researcher_id: str, distance: float = 0.0):
        member = ClusterMember(cluster_id=cluster_id, researcher_id=researcher_id, distance=distance)
        self.session.merge(member)
        self.session.flush()

    def get_latest_clusters(self) -> List[Cluster]:
        return (
            self.session.query(Cluster)
            .order_by(Cluster.run_date.desc())
            .limit(10)
            .all()
        )

    def get_cluster_members(self, cluster_id: str) -> List[ClusterMember]:
        return self.session.query(ClusterMember).filter_by(cluster_id=cluster_id).all()

    # ── Collaborations ────────────────────────────────────────
    def upsert_collaboration(self, a_id: str, b_id: str, score: float, reason: str):
        # Canonical order to avoid duplicates
        if a_id > b_id:
            a_id, b_id = b_id, a_id

        existing = (
            self.session.query(Collaboration)
            .filter_by(researcher_a_id=a_id, researcher_b_id=b_id)
            .first()
        )
        if existing:
            existing.score = score
            existing.reason = reason
        else:
            collab = Collaboration(
                researcher_a_id=a_id,
                researcher_b_id=b_id,
                score=score,
                reason=reason,
            )
            self.session.add(collab)
        self.session.flush()

    def get_collaborations_for(self, researcher_id: str, limit: int = 10) -> List[Collaboration]:
        return (
            self.session.query(Collaboration)
            .filter(
                (Collaboration.researcher_a_id == researcher_id) |
                (Collaboration.researcher_b_id == researcher_id)
            )
            .order_by(Collaboration.score.desc())
            .limit(limit)
            .all()
        )

    def get_all_collaborations(self, limit: int = 100) -> List[Collaboration]:
        return (
            self.session.query(Collaboration)
            .order_by(Collaboration.score.desc())
            .limit(limit)
            .all()
        )