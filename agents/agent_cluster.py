"""
agents/agent_cluster.py

Clusters researchers based on their expertise keywords and publication titles
using TF-IDF vectorisation + K-Means (scikit-learn — 100% free).

Steps:
  1. Build a text corpus: one document per researcher (expertise keywords + pub titles).
  2. Vectorise with TF-IDF.
  3. Reduce dimensions with Truncated SVD (LSA).
  4. Cluster with K-Means.
  5. Label each cluster by its top TF-IDF terms.
  6. Persist cluster + membership to DB.
"""
from typing import Dict, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import Pipeline

from agents.base_agent import BaseAgent
from database.connection import get_session
from database.repositories import ResearcherRepository, ClusterRepository
from config.settings import settings
from utils.logger import logger


class AgentCluster(BaseAgent):

    def __init__(self):
        super().__init__("AgentCluster")

    # ── Main ──────────────────────────────────────────────────
    def run(self, n_clusters: int = None) -> Dict:
        n_clusters = n_clusters or settings.agents.CLUSTERING_N_CLUSTERS

        # 1. Load researchers + build corpus
        researchers, corpus = self._build_corpus()
        if len(researchers) < n_clusters:
            logger.warning(
                f"[{self.name}] Only {len(researchers)} researchers — adjusting n_clusters to {max(2, len(researchers)//2)}"
            )
            n_clusters = max(2, len(researchers) // 2)

        if not researchers:
            logger.warning(f"[{self.name}] No researchers found. Skipping clustering.")
            return {"clusters": 0}

        # 2. Vectorise
        tfidf_matrix, vectorizer = self._vectorize(corpus)

        # 3. Dimensionality reduction
        lsa_matrix = self._reduce(tfidf_matrix, n_components=min(100, tfidf_matrix.shape[1] - 1))

        # 4. Cluster
        labels, distances = self._cluster(lsa_matrix, n_clusters)

        # 5. Generate cluster labels
        cluster_names = self._label_clusters(labels, corpus, vectorizer, n_clusters)

        # 6. Persist
        self._persist(researchers, labels, distances, cluster_names, n_clusters)

        logger.info(f"[{self.name}] Clustering done: {n_clusters} clusters from {len(researchers)} researchers.")
        return {"clusters": n_clusters, "researchers_clustered": len(researchers)}

    # ── Corpus builder ────────────────────────────────────────
    def _build_corpus(self) -> Tuple[list, List[str]]:
        with get_session() as session:
            r_repo = ResearcherRepository(session)
            researchers = r_repo.get_all(active_only=True)

            corpus = []
            for r in researchers:
                expertise = r_repo.get_expertise(r.researcher_id)
                parts = [r.name]
                if r.department:
                    parts.append(r.department)
                for exp in expertise:
                    parts.append(exp.area)
                    if exp.keywords:
                        parts.extend(exp.keywords)
                corpus.append(" ".join(parts).lower())

        return researchers, corpus

    # ── TF-IDF ────────────────────────────────────────────────
    def _vectorize(self, corpus: List[str]):
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        matrix = vectorizer.fit_transform(corpus)
        return matrix, vectorizer

    def _reduce(self, matrix, n_components: int):
        pipeline = Pipeline([
            ("svd", TruncatedSVD(n_components=n_components, random_state=42)),
            ("norm", Normalizer(copy=False)),
        ])
        return pipeline.fit_transform(matrix)

    # ── K-Means ───────────────────────────────────────────────
    def _cluster(self, matrix, n_clusters: int) -> Tuple[np.ndarray, np.ndarray]:
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
        labels = km.fit_predict(matrix)
        distances = np.min(km.transform(matrix), axis=1)
        return labels, distances

    # ── Cluster labelling ─────────────────────────────────────
    def _label_clusters(self, labels, corpus, vectorizer, n_clusters) -> Dict[int, str]:
        cluster_docs = {i: [] for i in range(n_clusters)}
        for idx, label in enumerate(labels):
            cluster_docs[label].append(corpus[idx])

        tfidf2 = TfidfVectorizer(max_features=50, stop_words="english")
        names = {}
        for cid, docs in cluster_docs.items():
            if not docs:
                names[cid] = f"Cluster {cid}"
                continue
            try:
                mat = tfidf2.fit_transform(docs)
                top_idx = np.argsort(mat.sum(axis=0).A1)[-3:][::-1]
                top_terms = [tfidf2.get_feature_names_out()[i] for i in top_idx]
                names[cid] = " / ".join(top_terms).title()
            except Exception:
                names[cid] = f"Cluster {cid}"
        return names

    # ── Persist ───────────────────────────────────────────────
    def _persist(self, researchers, labels, distances, cluster_names, n_clusters):
        with get_session() as session:
            c_repo = ClusterRepository(session)

            cluster_ids = {}
            for cid in range(n_clusters):
                cluster = c_repo.create_cluster({
                    "name": cluster_names.get(cid, f"Cluster {cid}"),
                    "algorithm": "kmeans",
                    "parameters": {"n_clusters": n_clusters},
                })
                cluster_ids[cid] = cluster.cluster_id

            for idx, researcher in enumerate(researchers):
                c_repo.add_member(
                    cluster_id=cluster_ids[int(labels[idx])],
                    researcher_id=researcher.researcher_id,
                    distance=float(distances[idx]),
                )
                self._increment()
