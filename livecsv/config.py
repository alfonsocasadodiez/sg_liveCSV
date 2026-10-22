"""Configuration model: persisted JSON on disk, overridable by environment variables.

Precedence for every field: environment variable > stored config.json > built-in default.
Fields overridden by an environment variable are reported back to the GUI as read-only,
since saving from the GUI can never change a value an env var is pinning.
"""
import copy
import json
import os
import threading

from .crypto import SecretBox

DEFAULT_INTERVAL_MINUTES = 10

DEFAULT_CONFIG = {
    "connection": {
        "server_url": "",
        "script_name": "",
        "script_secret": "",
    },
    "interval_minutes": DEFAULT_INTERVAL_MINUTES,
    "exports": [],
}


def _env(name, default=None):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


class ConfigStore:
    """Thread-safe load/save of config.json, merged with environment overrides."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.config_path = os.path.join(data_dir, "config.json")
        self.secret_box = SecretBox(os.path.join(data_dir, "secret.key"))
        self._lock = threading.Lock()
        os.makedirs(data_dir, exist_ok=True)

    # ---- raw persisted config (secrets stay encrypted on disk) ----

    def _read_raw(self) -> dict:
        if not os.path.exists(self.config_path):
            return copy.deepcopy(DEFAULT_CONFIG)
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = copy.deepcopy(DEFAULT_CONFIG)
        merged.update(data)
        merged["connection"] = {**DEFAULT_CONFIG["connection"], **data.get("connection", {})}
        return merged

    def _write_raw(self, data: dict):
        tmp_path = self.config_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.config_path)

    # ---- env override bookkeeping ----

    @staticmethod
    def _exports_env():
        raw = _env("SG_LIVECSV_EXPORTS_JSON")
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def env_overrides(self) -> dict:
        """Which top-level/connection fields are currently pinned by an env var."""
        return {
            "server_url": _env("SG_SERVER_URL") is not None,
            "script_name": _env("SG_SCRIPT_NAME") is not None,
            "script_secret": _env("SG_SCRIPT_SECRET") is not None,
            "interval_minutes": _env("SG_INTERVAL_MINUTES") is not None,
            "exports": self._exports_env() is not None,
            "output_dir": _env("SG_OUTPUT_DIR") is not None,
        }

    # ---- effective config, with env overrides applied and secrets decrypted ----

    def get_effective(self) -> dict:
        with self._lock:
            raw = self._read_raw()

        overrides = self.env_overrides()
        output_dir = _env("SG_OUTPUT_DIR", "/data/csv")

        connection = {
            "server_url": _env("SG_SERVER_URL", raw["connection"]["server_url"]),
            "script_name": _env("SG_SCRIPT_NAME", raw["connection"]["script_name"]),
            "script_secret": _env(
                "SG_SCRIPT_SECRET", self.secret_box.decrypt(raw["connection"]["script_secret"])
            ),
        }

        interval_env = _env("SG_INTERVAL_MINUTES")
        interval_minutes = (
            int(interval_env) if interval_env is not None else raw.get("interval_minutes", DEFAULT_INTERVAL_MINUTES)
        )

        exports_env = self._exports_env()
        exports = exports_env if exports_env is not None else raw.get("exports", [])
        # Normalize output paths to live under output_dir unless an absolute path was given.
        normalized_exports = []
        for export in exports:
            export = dict(export)
            file_name = export.get("file_name") or f"{export.get('name', export.get('entity_type', 'export'))}.csv"
            export["file_name"] = file_name
            export["output_path"] = os.path.join(output_dir, file_name)
            normalized_exports.append(export)

        return {
            "connection": connection,
            "interval_minutes": interval_minutes,
            "exports": normalized_exports,
            "output_dir": output_dir,
            "env_overrides": overrides,
        }

    def save(self, payload: dict):
        """Persist GUI-submitted config. Fields pinned by env vars are ignored (not overwritten)."""
        overrides = self.env_overrides()
        with self._lock:
            raw = self._read_raw()

            connection = payload.get("connection", {})
            if not overrides["server_url"] and "server_url" in connection:
                raw["connection"]["server_url"] = connection["server_url"]
            if not overrides["script_name"] and "script_name" in connection:
                raw["connection"]["script_name"] = connection["script_name"]
            if not overrides["script_secret"] and connection.get("script_secret"):
                raw["connection"]["script_secret"] = self.secret_box.encrypt(connection["script_secret"])

            if not overrides["interval_minutes"] and "interval_minutes" in payload:
                raw["interval_minutes"] = int(payload["interval_minutes"])

            if not overrides["exports"] and "exports" in payload:
                raw["exports"] = payload["exports"]

            self._write_raw(raw)

        return self.get_effective()
