"""Background loop that periodically fetches data from ShotGrid and writes CSV files."""
import csv
import logging
import os
import threading
import time

from . import sg_client

logger = logging.getLogger("livecsv.exporter")


class ExportStatus:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_run_at = None
        self.last_success_at = None
        self.last_error = None
        self.next_run_at = None
        self.running = False
        self.per_export = {}

    def snapshot(self):
        with self.lock:
            return {
                "last_run_at": self.last_run_at,
                "last_success_at": self.last_success_at,
                "last_error": self.last_error,
                "next_run_at": self.next_run_at,
                "running": self.running,
                "per_export": dict(self.per_export),
            }


def write_csv(data, file_path, fields):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            flat_row = {}
            for key, value in row.items():
                if isinstance(value, dict):
                    flat_row[key] = value.get("name", value)
                elif isinstance(value, list):
                    flat_row[key] = ", ".join(
                        str(v.get("name", v)) if isinstance(v, dict) else str(v) for v in value
                    )
                else:
                    flat_row[key] = value
            writer.writerow(flat_row)
    os.replace(tmp_path, file_path)


class Exporter:
    """Runs the fetch/write loop on a background thread, reloading config each cycle."""

    def __init__(self, config_store):
        self.config_store = config_store
        self.status = ExportStatus()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._wake_event.set()

    def trigger_now(self):
        self._wake_event.set()

    def _loop(self):
        while not self._stop_event.is_set():
            self.run_once()
            interval_minutes = self.config_store.get_effective().get("interval_minutes", 10)
            with self.status.lock:
                self.status.next_run_at = time.time() + interval_minutes * 60
            self._wake_event.wait(timeout=max(interval_minutes * 60, 1))
            self._wake_event.clear()

    def run_once(self):
        with self.status.lock:
            self.status.running = True
            self.status.last_run_at = time.time()
            self.status.last_error = None

        config = self.config_store.get_effective()
        connection = config["connection"]
        per_export_status = {}
        error = None

        if not connection.get("server_url") or not connection.get("script_name") or not connection.get("script_secret"):
            error = "ShotGrid connection is not fully configured."
        else:
            for export in config.get("exports", []):
                name = export.get("name", export.get("entity_type", "export"))
                try:
                    data = sg_client.fetch_data(
                        connection,
                        export["entity_type"],
                        export["fields"],
                        export.get("filters"),
                    )
                    write_csv(data, export["output_path"], export["fields"])
                    per_export_status[name] = {"ok": True, "row_count": len(data), "updated_at": time.time()}
                except Exception as exc:  # noqa: BLE001 - surface any failure to the GUI/status
                    logger.exception("Export %s failed", name)
                    per_export_status[name] = {"ok": False, "error": str(exc), "updated_at": time.time()}
                    error = f"Export '{name}' failed: {exc}"

        with self.status.lock:
            self.status.running = False
            self.status.per_export = per_export_status
            self.status.last_error = error
            if error is None:
                self.status.last_success_at = time.time()
