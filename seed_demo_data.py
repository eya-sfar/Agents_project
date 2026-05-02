"""
seed_demo_data.py
Populates the database with realistic demo data so you can explore
the dashboard without running the scrapers.

Usage:
    python seed_demo_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database.connection import init_db, get_session
from database.repositories import (
    LabRepository, ResearcherRepository,
    PublicationRepository, ClusterRepository,
)
from agents.agent_expertise_matcher import AgentExpertiseMatcher
from agents.agent_cluster import AgentCluster
from agents.agent_collab_advisor import AgentCollabAdvisor
from agents.agent_negotiator import AgentNegotiator
from utils.logger import logger

LABS = [
    {"name": "AI & Machine Learning Lab", "department": "Computer Science", "university": "Tech University", "country": "Tunisia", "num_researchers": 12, "active_projects": 5},
    {"name": "NLP Research Centre", "department": "Computational Linguistics", "university": "Tech University", "country": "Tunisia", "num_researchers": 8, "active_projects": 3},
    {"name": "Bioinformatics Unit", "department": "Biology", "university": "Science University", "country": "Tunisia", "num_researchers": 6, "active_projects": 2},
    {"name": "Cybersecurity Lab", "department": "Computer Science", "university": "Tech University", "country": "Tunisia", "num_researchers": 10, "active_projects": 4},
    {"name": "Distributed Systems Group", "department": "Computer Science", "university": "Engineering University", "country": "Tunisia", "num_researchers": 7, "active_projects": 3},
]

RESEARCHERS = [
    {"name": "Dr. Amira Bouaziz", "department": "Computer Science", "position": "Professor", "h_index": 18, "total_citations": 1450, "publications": 42},
    {"name": "Prof. Karim Ben Ali", "department": "Computer Science", "position": "Professor", "h_index": 24, "total_citations": 3200, "publications": 68},
    {"name": "Dr. Leila Mansouri", "department": "Computational Linguistics", "position": "Associate Professor", "h_index": 12, "total_citations": 890, "publications": 31},
    {"name": "Dr. Youssef Trabelsi", "department": "Biology", "position": "Assistant Professor", "h_index": 9, "total_citations": 430, "publications": 18},
    {"name": "Prof. Sonia Khelifi", "department": "Computer Science", "position": "Professor", "h_index": 21, "total_citations": 2700, "publications": 55},
    {"name": "Dr. Mohamed Jarray", "department": "Computer Science", "position": "Associate Professor", "h_index": 15, "total_citations": 1100, "publications": 36},
    {"name": "Dr. Nadia Zouari", "department": "Biology", "position": "Assistant Professor", "h_index": 7, "total_citations": 280, "publications": 14},
    {"name": "Prof. Ali Ouertani", "department": "Computer Science", "position": "Professor", "h_index": 29, "total_citations": 4100, "publications": 82},
    {"name": "Dr. Fatma Mejri", "department": "Computational Linguistics", "position": "PhD Candidate", "h_index": 4, "total_citations": 120, "publications": 9},
    {"name": "Dr. Bilel Hamdi", "department": "Computer Science", "position": "Associate Professor", "h_index": 16, "total_citations": 1350, "publications": 38},
    {"name": "Prof. Rania Chaabane", "department": "Computer Science", "position": "Professor", "h_index": 22, "total_citations": 2900, "publications": 61},
    {"name": "Dr. Omar Mabrouk", "department": "Biology", "position": "Assistant Professor", "h_index": 8, "total_citations": 360, "publications": 16},
]

PUBLICATIONS = [
    {"title": "Deep Learning for Arabic Text Classification", "year": 2023, "citations": 45, "venue": "ACL", "pub_type": "conference"},
    {"title": "Transformer-based Named Entity Recognition in Low-Resource Languages", "year": 2022, "citations": 78, "venue": "EMNLP", "pub_type": "conference"},
    {"title": "Federated Learning for Privacy-Preserving Healthcare Analytics", "year": 2023, "citations": 92, "venue": "Nature Communications", "pub_type": "journal"},
    {"title": "Graph Neural Networks for Protein Structure Prediction", "year": 2023, "citations": 134, "venue": "Bioinformatics", "pub_type": "journal"},
    {"title": "Adversarial Attacks on Machine Learning Models", "year": 2022, "citations": 167, "venue": "IEEE S&P", "pub_type": "conference"},
    {"title": "Efficient Kubernetes Cluster Scheduling with Reinforcement Learning", "year": 2023, "citations": 38, "venue": "ICDCS", "pub_type": "conference"},
    {"title": "Arabic Dialect Identification Using BERT", "year": 2021, "citations": 89, "venue": "LREC", "pub_type": "conference"},
    {"title": "Intrusion Detection System using Deep Neural Networks", "year": 2022, "citations": 112, "venue": "Computers & Security", "pub_type": "journal"},
    {"title": "Genomic Variant Classification with CNN", "year": 2023, "citations": 56, "venue": "PLOS ONE", "pub_type": "journal"},
    {"title": "Explainable AI for Medical Diagnosis", "year": 2023, "citations": 203, "venue": "Artificial Intelligence in Medicine", "pub_type": "journal"},
    {"title": "Zero-Shot Learning for Image Recognition", "year": 2022, "citations": 145, "venue": "CVPR", "pub_type": "conference"},
    {"title": "Blockchain-based Secure Data Sharing in IoT", "year": 2023, "citations": 67, "venue": "IEEE IoT Journal", "pub_type": "journal"},
    {"title": "Multi-label Text Classification with Attention Mechanism", "year": 2021, "citations": 98, "venue": "IJCAI", "pub_type": "conference"},
    {"title": "Quantum-Inspired Optimization for Scheduling Problems", "year": 2023, "citations": 29, "venue": "GECCO", "pub_type": "conference"},
    {"title": "RNA Secondary Structure Prediction Using Deep Learning", "year": 2022, "citations": 72, "venue": "Nucleic Acids Research", "pub_type": "journal"},
]

EXPERTISE_MAP = {
    "Dr. Amira Bouaziz":    [("Machine Learning", ["deep learning", "classification", "neural network"])],
    "Prof. Karim Ben Ali":  [("Natural Language Processing", ["nlp", "bert", "transformer"]), ("Machine Learning", ["text classification"])],
    "Dr. Leila Mansouri":   [("Natural Language Processing", ["arabic nlp", "language model", "sentiment"])],
    "Dr. Youssef Trabelsi": [("Bioinformatics", ["genomics", "protein", "sequence alignment"])],
    "Prof. Sonia Khelifi":  [("Cybersecurity", ["intrusion detection", "malware", "encryption"])],
    "Dr. Mohamed Jarray":   [("Distributed Systems", ["kubernetes", "cloud", "scheduling"])],
    "Dr. Nadia Zouari":     [("Bioinformatics", ["rna", "dna", "bioinformatics"])],
    "Prof. Ali Ouertani":   [("Machine Learning", ["computer vision", "image", "cnn"]), ("Cybersecurity", ["adversarial attacks"])],
    "Dr. Fatma Mejri":      [("Natural Language Processing", ["dialect identification", "bert", "arabic"])],
    "Dr. Bilel Hamdi":      [("Networks", ["iot", "blockchain", "protocol"])],
    "Prof. Rania Chaabane": [("Machine Learning", ["explainability", "medical ai", "deep learning"])],
    "Dr. Omar Mabrouk":     [("Bioinformatics", ["rna", "genomic", "deep learning"])],
}


def seed():
    init_db()
    logger.info("Seeding demo data …")

    lab_ids = {}
    with get_session() as session:
        lab_repo = LabRepository(session)
        for lab_data in LABS:
            existing = lab_repo.search(lab_data["name"])
            if existing:
                lab_ids[lab_data["name"]] = existing[0].lab_id
            else:
                lab = lab_repo.create(lab_data)
                lab_ids[lab_data["name"]] = lab.lab_id
    logger.info(f"  Labs: {len(lab_ids)}")

    # Assign researchers round-robin to labs
    lab_names = list(lab_ids.keys())
    r_ids = {}
    with get_session() as session:
        r_repo = ResearcherRepository(session)
        for i, r_data in enumerate(RESEARCHERS):
            existing = r_repo.search(r_data["name"])
            if existing:
                r_ids[r_data["name"]] = existing[0].researcher_id
                continue
            r_data["lab_id"] = lab_ids[lab_names[i % len(lab_names)]]
            r = r_repo.create(r_data)
            r_ids[r_data["name"]] = r.researcher_id
    logger.info(f"  Researchers: {len(r_ids)}")

    # Publications — assign first 2 researchers as co-authors
    r_list = list(r_ids.values())
    with get_session() as session:
        pub_repo = PublicationRepository(session)
        for i, pub_data in enumerate(PUBLICATIONS):
            if pub_repo.get_all(limit=500):
                # check by title approximate
                pass
            author_ids = [r_list[i % len(r_list)], r_list[(i + 1) % len(r_list)]]
            pub_repo.create(pub_data, author_ids=author_ids)
    logger.info(f"  Publications: {len(PUBLICATIONS)}")

    # Expertise
    with get_session() as session:
        r_repo = ResearcherRepository(session)
        for name, areas in EXPERTISE_MAP.items():
            rid = r_ids.get(name)
            if not rid:
                continue
            for area, keywords in areas:
                r_repo.upsert_expertise(rid, area, keywords, score=0.9, source="manual")
    logger.info("  Expertise: done")

    # Run analysis agents
    logger.info("Running clustering …")
    AgentCluster().start(n_clusters=4)

    logger.info("Running collaboration advisor …")
    AgentCollabAdvisor().start()

    logger.info("Running negotiator …")
    AgentNegotiator().start()

    logger.info("✅ Demo data seeded successfully!")


if __name__ == "__main__":
    seed()
