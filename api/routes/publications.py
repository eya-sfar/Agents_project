"""
api/routes/publications.py
"""
from flask import request
from flask_restx import Namespace, Resource

from database.connection import get_session
from database.repositories import PublicationRepository

ns = Namespace("publications", description="Publication operations")


@ns.route("/")
class PublicationList(Resource):
    def get(self):
        limit = int(request.args.get("limit", 100))
        with get_session() as session:
            pubs = PublicationRepository(session).get_all(limit=limit)
            return [p.to_dict() for p in pubs], 200


@ns.route("/<string:pub_id>")
class PublicationDetail(Resource):
    def get(self, pub_id):
        with get_session() as session:
            pub = PublicationRepository(session).get_by_id(pub_id)
            if not pub:
                ns.abort(404)
            return pub.to_dict(), 200


@ns.route("/top-cited")
class TopCited(Resource):
    def get(self):
        limit = int(request.args.get("limit", 20))
        with get_session() as session:
            pubs = PublicationRepository(session).get_top_cited(limit)
            return [p.to_dict() for p in pubs], 200


@ns.route("/researcher/<string:researcher_id>")
class PublicationsByResearcher(Resource):
    def get(self, researcher_id):
        with get_session() as session:
            pubs = PublicationRepository(session).get_by_researcher(researcher_id)
            return [p.to_dict() for p in pubs], 200
