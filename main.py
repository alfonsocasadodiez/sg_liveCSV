"""Entrypoint: serves the GUI/API and runs the background CSV export loop."""
import os

from livecsv.webapp import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
