"""
api/routes/clusters.py
"""
from flask import request
from flask_restx import Namespace, Resource

from database.connection import get_session
from database.repositories import ClusterRepository

ns = Namespace("clusters", description="Cluster & collaboration operations")


@ns.route("/")
class ClusterList(Resource):
    def get(self):
        with get_session() as session:
            clusters = ClusterRepository(session).get_latest_clusters()
            result = []
            for c in clusters:
                d = c.to_dict()
                d["member_count"] = len(c.members)
                result.append(d)
            return result, 200


@ns.route("/<string:cluster_id>/members")
class ClusterMembers(Resource):
    def get(self, cluster_id):
        with get_session() as session:
            members = ClusterRepository(session).get_cluster_members(cluster_id)
            return [
                {"researcher_id": m.researcher_id, "distance": m.distance}
                for m in members
            ], 200


@ns.route("/collaborations")
class CollaborationList(Resource):
    def get(self):
        limit = int(request.args.get("limit", 50))
        with get_session() as session:
            collabs = ClusterRepository(session).get_all_collaborations(limit=limit)
            return [c.to_dict() for c in collabs], 200


@ns.route("/collaborations/researcher/<string:researcher_id>")
class ResearcherCollaborations(Resource):
    def get(self, researcher_id):
        limit = int(request.args.get("limit", 10))
        with get_session() as session:
            collabs = ClusterRepository(session).get_collaborations_for(researcher_id, limit)
            return [c.to_dict() for c in collabs], 200
