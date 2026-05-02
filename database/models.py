"""
database/models.py
SQLAlchemy ORM models mirroring the PostgreSQL schema.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, ARRAY, JSON, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def new_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# Lab
# ─────────────────────────────────────────────
class Lab(Base):
    __tablename__ = "labs"

    lab_id          = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name            = Column(String(255), nullable=False)
    department      = Column(String(255))
    university      = Column(String(255))
    country         = Column(String(100))
    website         = Column(Text)
    description     = Column(Text)
    num_researchers = Column(Integer, default=0)
    active_projects = Column(Integer, default=0)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    researchers = relationship("Researcher", back_populates="lab")

    def to_dict(self):
        return {
            "lab_id": self.lab_id,
            "name": self.name,
            "department": self.department,
            "university": self.university,
            "country": self.country,
            "website": self.website,
            "description": self.description,
            "num_researchers": self.num_researchers,
            "active_projects": self.active_projects,
        }


# ─────────────────────────────────────────────
# Researcher
# ─────────────────────────────────────────────
class Researcher(Base):
    __tablename__ = "researchers"

    researcher_id     = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name              = Column(String(255), nullable=False)
    email             = Column(String(255))
    lab_id            = Column(UUID(as_uuid=False), ForeignKey("labs.lab_id"), nullable=True)
    department        = Column(String(255))
    position          = Column(String(100))
    h_index           = Column(Integer, default=0)
    total_citations   = Column(Integer, default=0)
    publications      = Column(Integer, default=0)
    google_scholar_id = Column(String(50))
    dblp_pid          = Column(String(100))
    orcid             = Column(String(50))
    profile_url       = Column(Text)
    is_active         = Column(Boolean, default=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lab              = relationship("Lab", back_populates="researchers")
    expertise_areas  = relationship("Expertise", back_populates="researcher", cascade="all, delete-orphan")
    authored_pubs    = relationship("PublicationAuthor", back_populates="researcher")

    def to_dict(self):
        return {
            "researcher_id": self.researcher_id,
            "name": self.name,
            "email": self.email,
            "lab_id": self.lab_id,
            "department": self.department,
            "position": self.position,
            "h_index": self.h_index,
            "total_citations": self.total_citations,
            "publications": self.publications,
            "google_scholar_id": self.google_scholar_id,
            "orcid": self.orcid,
            "is_active": self.is_active,
        }


# ─────────────────────────────────────────────
# Publication
# ─────────────────────────────────────────────
class Publication(Base):
    __tablename__ = "publications"

    publication_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    title          = Column(Text, nullable=False)
    abstract       = Column(Text)
    year           = Column(Integer)
    citations      = Column(Integer, default=0)
    venue          = Column(String(255))
    doi            = Column(String(200))
    url            = Column(Text)
    pub_type       = Column(String(50))
    created_at     = Column(DateTime, default=datetime.utcnow)

    authors = relationship("PublicationAuthor", back_populates="publication")

    def to_dict(self):
        return {
            "publication_id": self.publication_id,
            "title": self.title,
            "abstract": self.abstract,
            "year": self.year,
            "citations": self.citations,
            "venue": self.venue,
            "doi": self.doi,
            "pub_type": self.pub_type,
        }


class PublicationAuthor(Base):
    __tablename__ = "publication_authors"

    publication_id = Column(UUID(as_uuid=False), ForeignKey("publications.publication_id"), primary_key=True)
    researcher_id  = Column(UUID(as_uuid=False), ForeignKey("researchers.researcher_id"), primary_key=True)
    author_order   = Column(Integer, default=1)

    publication = relationship("Publication", back_populates="authors")
    researcher  = relationship("Researcher", back_populates="authored_pubs")


# ─────────────────────────────────────────────
# Expertise
# ─────────────────────────────────────────────
class Expertise(Base):
    __tablename__ = "expertise"

    expertise_id  = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    researcher_id = Column(UUID(as_uuid=False), ForeignKey("researchers.researcher_id"), nullable=False)
    area          = Column(String(255), nullable=False)
    keywords      = Column(ARRAY(String))
    score         = Column(Float, default=1.0)
    source        = Column(String(50), default="manual")
    created_at    = Column(DateTime, default=datetime.utcnow)

    researcher = relationship("Researcher", back_populates="expertise_areas")

    def to_dict(self):
        return {
            "expertise_id": self.expertise_id,
            "researcher_id": self.researcher_id,
            "area": self.area,
            "keywords": self.keywords or [],
            "score": self.score,
            "source": self.source,
        }


# ─────────────────────────────────────────────
# Cluster
# ─────────────────────────────────────────────
class Cluster(Base):
    __tablename__ = "clusters"

    cluster_id  = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name        = Column(String(255))
    description = Column(Text)
    algorithm   = Column(String(50), default="kmeans")
    run_date    = Column(DateTime, default=datetime.utcnow)
    parameters  = Column(JSON)

    members = relationship("ClusterMember", back_populates="cluster", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "description": self.description,
            "algorithm": self.algorithm,
            "run_date": str(self.run_date),
            "parameters": self.parameters,
        }


class ClusterMember(Base):
    __tablename__ = "cluster_members"

    cluster_id    = Column(UUID(as_uuid=False), ForeignKey("clusters.cluster_id"), primary_key=True)
    researcher_id = Column(UUID(as_uuid=False), ForeignKey("researchers.researcher_id"), primary_key=True)
    distance      = Column(Float, default=0.0)

    cluster    = relationship("Cluster", back_populates="members")
    researcher = relationship("Researcher")


# ─────────────────────────────────────────────
# Collaboration
# ─────────────────────────────────────────────
class Collaboration(Base):
    __tablename__ = "collaborations"
    __table_args__ = (UniqueConstraint("researcher_a_id", "researcher_b_id"),)

    collab_id       = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    researcher_a_id = Column(UUID(as_uuid=False), ForeignKey("researchers.researcher_id"), nullable=False)
    researcher_b_id = Column(UUID(as_uuid=False), ForeignKey("researchers.researcher_id"), nullable=False)
    score           = Column(Float, nullable=False)
    reason          = Column(Text)
    status          = Column(String(50), default="suggested")
    created_at      = Column(DateTime, default=datetime.utcnow)

    researcher_a = relationship("Researcher", foreign_keys=[researcher_a_id])
    researcher_b = relationship("Researcher", foreign_keys=[researcher_b_id])

    def to_dict(self):
        return {
            "collab_id": self.collab_id,
            "researcher_a_id": self.researcher_a_id,
            "researcher_b_id": self.researcher_b_id,
            "score": self.score,
            "reason": self.reason,
            "status": self.status,
        }


# ─────────────────────────────────────────────
# Agent Run (audit)
# ─────────────────────────────────────────────
class AgentRun(Base):
    __tablename__ = "agent_runs"

    run_id             = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    agent_name         = Column(String(100), nullable=False)
    status             = Column(String(50), default="started")
    records_processed  = Column(Integer, default=0)
    error_message      = Column(Text)
    started_at         = Column(DateTime, default=datetime.utcnow)
    finished_at        = Column(DateTime)

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "records_processed": self.records_processed,
            "error_message": self.error_message,
            "started_at": str(self.started_at),
            "finished_at": str(self.finished_at) if self.finished_at else None,
        }