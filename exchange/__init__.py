"""Flask application for the classroom blockchain exchange."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

from .blockchain import Blockchain


def create_app(blockchain: Blockchain | None = None) -> Flask:
    """Build a Flask app around one in-memory chain.

    Pass ``blockchain`` from tests so each test gets a fresh chain.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    app.json.sort_keys = False
    debug = os.environ.get("EXCHANGE_DEBUG", "").lower() in {"1", "true", "yes"}
    app.config["DEBUG"] = debug
    app.config["BLOCKCHAIN"] = blockchain if blockchain is not None else Blockchain()

    from .api import api
    from .routes import pages

    app.register_blueprint(api)
    app.register_blueprint(pages)

    @app.after_request
    def _security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(413)
    def _too_large(_error):
        return jsonify(error="The form was too large."), 413

    return app
