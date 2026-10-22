"""Flask app: GUI for configuring the live CSV export, plus the CSV download endpoint."""
import os

from flask import Flask, jsonify, render_template, request, send_from_directory

from . import sg_client
from .config import ConfigStore
from .exporter import Exporter

DATA_DIR = os.environ.get("SG_LIVECSV_DATA_DIR", "/data")


def _redact(effective_config: dict) -> dict:
    redacted = dict(effective_config)
    connection = dict(redacted["connection"])
    connection["script_secret_set"] = bool(connection.pop("script_secret", ""))
    redacted["connection"] = connection
    return redacted


def create_app():
    app = Flask(__name__)
    config_store = ConfigStore(DATA_DIR)
    exporter = Exporter(config_store)
    exporter.start()

    app.config_store = config_store
    app.exporter = exporter

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/config")
    def get_config():
        return jsonify(_redact(config_store.get_effective()))

    @app.post("/api/config")
    def save_config():
        payload = request.get_json(force=True) or {}
        updated = config_store.save(payload)
        exporter.trigger_now()
        return jsonify(_redact(updated))

    @app.post("/api/connection/test")
    def test_connection():
        payload = request.get_json(force=True) or {}
        connection = payload.get("connection") or config_store.get_effective()["connection"]
        try:
            result = sg_client.test_connection(connection)
            return jsonify({"ok": True, "info": result.get("server_info", {})})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/schema/entities")
    def schema_entities():
        connection = config_store.get_effective()["connection"]
        try:
            return jsonify({"ok": True, "entities": sg_client.list_entity_types(connection)})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/schema/fields/<entity_type>")
    def schema_fields(entity_type):
        connection = config_store.get_effective()["connection"]
        try:
            return jsonify({"ok": True, "fields": sg_client.list_entity_fields(connection, entity_type)})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/status")
    def status():
        return jsonify(exporter.status.snapshot())

    @app.post("/api/run-now")
    def run_now():
        exporter.trigger_now()
        return jsonify({"ok": True})

    @app.get("/csv/<path:filename>")
    def serve_csv(filename):
        output_dir = config_store.get_effective()["output_dir"]
        return send_from_directory(output_dir, filename)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
