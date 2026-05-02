"""
api/routes/researchers.py
REST endpoints for Researcher resources.
"""
from flask import request
from flask_restx import Namespace, Resource, fields

from database.connection import get_session
from database.repositories import ResearcherRepository

ns = Namespace("researchers", description="Researcher operations")

researcher_model = ns.model("Researcher", {
    "researcher_id": fields.String(readonly=True),
    "name": fields.String(required=True),
    "email": fields.String,
    "lab_id": fields.String,
    "department": fields.String,
    "position": fields.String,
    "h_index": fields.Integer,
    "total_citations": fields.Integer,
    "publications": fields.Integer,
    "google_scholar_id": fields.String,
    "orcid": fields.String,
    "is_active": fields.Boolean,
})


@ns.route("/")
class ResearcherList(Resource):

    @ns.doc("list_researchers")
    def get(self):
        """List all researchers."""
        active_only = request.args.get("active", "true").lower() == "true"
        with get_session() as session:
            repo = ResearcherRepository(session)
            items = repo.get_all(active_only=active_only)
            return [r.to_dict() for r in items], 200

    @ns.expect(researcher_model)
    @ns.doc("create_researcher")
    def post(self):
        """Create a new researcher."""
        data = ns.payload
        with get_session() as session:
            repo = ResearcherRepository(session)
            r = repo.create(data)
            return r.to_dict(), 201


@ns.route("/<string:researcher_id>")
@ns.param("researcher_id", "Researcher UUID")
class ResearcherDetail(Resource):

    @ns.doc("get_researcher")
    def get(self, researcher_id):
        with get_session() as session:
            r = ResearcherRepository(session).get_by_id(researcher_id)
            if not r:
                ns.abort(404, "Researcher not found")
            return r.to_dict(), 200

    @ns.doc("update_researcher")
    def put(self, researcher_id):
        data = request.json or {}
        with get_session() as session:
            r = ResearcherRepository(session).update(researcher_id, data)
            if not r:
                ns.abort(404, "Researcher not found")
            return r.to_dict(), 200

    @ns.doc("delete_researcher")
    def delete(self, researcher_id):
        with get_session() as session:
            ok = ResearcherRepository(session).delete(researcher_id)
            if not ok:
                ns.abort(404, "Researcher not found")
            return {"message": "Deleted"}, 200


@ns.route("/search/<string:query>")
class ResearcherSearch(Resource):

    @ns.doc("search_researchers")
    def get(self, query):
        with get_session() as session:
            items = ResearcherRepository(session).search(query)
            return [r.to_dict() for r in items], 200


@ns.route("/<string:researcher_id>/expertise")
class ResearcherExpertise(Resource):

    @ns.doc("get_expertise")
    def get(self, researcher_id):
        with get_session() as session:
            repo = ResearcherRepository(session)
            r = repo.get_by_id(researcher_id)
            if not r:
                ns.abort(404, "Researcher not found")
            expertise = repo.get_expertise(researcher_id)
            return [e.to_dict() for e in expertise], 200


@ns.route("/stats/top-h-index")
class TopHIndex(Resource):

    @ns.doc("top_h_index")
    def get(self):
        limit = int(request.args.get("limit", 10))
        with get_session() as session:
            items = ResearcherRepository(session).get_top_by_h_index(limit)
            return [r.to_dict() for r in items], 200
