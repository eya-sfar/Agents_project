"""
api/routes/labs.py
"""
from flask import request
from flask_restx import Namespace, Resource

from database.connection import get_session
from database.repositories import LabRepository

ns = Namespace("labs", description="Laboratory operations")


@ns.route("/")
class LabList(Resource):
    def get(self):
        with get_session() as session:
            return [l.to_dict() for l in LabRepository(session).get_all()], 200

    def post(self):
        with get_session() as session:
            lab = LabRepository(session).create(ns.payload or request.json)
            return lab.to_dict(), 201


@ns.route("/<string:lab_id>")
class LabDetail(Resource):
    def get(self, lab_id):
        with get_session() as session:
            lab = LabRepository(session).get_by_id(lab_id)
            if not lab:
                ns.abort(404)
            return lab.to_dict(), 200

    def put(self, lab_id):
        with get_session() as session:
            lab = LabRepository(session).update(lab_id, request.json or {})
            if not lab:
                ns.abort(404)
            return lab.to_dict(), 200

    def delete(self, lab_id):
        with get_session() as session:
            ok = LabRepository(session).delete(lab_id)
            return ({"message": "Deleted"}, 200) if ok else ns.abort(404)
