"""
api/routes/agents.py
Trigger agent pipelines via HTTP.
"""
import threading
from flask import request
from flask_restx import Namespace, Resource

from utils.logger import logger

ns = Namespace("agents", description="Trigger MAS agent pipelines")


def _run_pipeline_async(kwargs):
    from agents import AgentCoordinator
    coordinator = AgentCoordinator()
    coordinator.start(**kwargs)


@ns.route("/run/full-pipeline")
class FullPipeline(Resource):
    def post(self):
        """
        Trigger the full MAS pipeline asynchronously.
        Body (optional):
          {
            "seed_researchers": ["Alice Smith", "Bob Jones"],
            "institution_name": "Universite de Tunis El Manar",
            "country_code": "TN",
            "topic": "machine learning",
            "skip_scrape": false,
            "n_clusters": 8,
            "max_authors": 200
          }
        """
        payload = request.json or {}
        thread = threading.Thread(
            target=_run_pipeline_async,
            args=(payload,),
            daemon=True,
        )
        thread.start()
        return {"message": "Pipeline started", "async": True}, 202


@ns.route("/run/clustering")
class RunClustering(Resource):
    def post(self):
        """Re-run clustering only."""
        from agents import AgentCluster
        payload = request.json or {}
        n = payload.get("n_clusters", 8)

        def _run():
            AgentCluster().start(n_clusters=n)

        threading.Thread(target=_run, daemon=True).start()
        return {"message": f"Clustering started with n_clusters={n}"}, 202


@ns.route("/run/collaborations")
class RunCollaborations(Resource):
    def post(self):
        """Re-run collaboration advisor only."""
        from agents import AgentCollabAdvisor, AgentNegotiator

        def _run():
            AgentCollabAdvisor().start()
            AgentNegotiator().start()

        threading.Thread(target=_run, daemon=True).start()
        return {"message": "Collaboration & negotiation agents started"}, 202


@ns.route("/runs")
class AgentRuns(Resource):
    def get(self):
        """List recent agent run audit logs."""
        from database.connection import get_session
        from database.models import AgentRun
        with get_session() as session:
            runs = (
                session.query(AgentRun)
                .order_by(AgentRun.started_at.desc())
                .limit(50)
                .all()
            )
            return [r.to_dict() for r in runs], 200
