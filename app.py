"""Flask application for Envanter.

This server serves the compiled front-end so that navigating directly to the
server's IP address displays the login screen handled by the React app. Any
unknown route will be routed to ``index.html`` allowing React Router to manage
client-side navigation.
"""

from pathlib import Path

from flask import Flask, send_from_directory


BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str) -> str:
    """Serve the React single page application.

    If ``path`` points to an existing file, that file is served directly. For
    any other route, ``index.html`` is returned so the client-side router can
    take over. This ensures that visiting the server's root IP displays the
    login page.
    """

    file_path = BASE_DIR / path
    if path and file_path.exists():
        return send_from_directory(str(BASE_DIR), path)
    return send_from_directory(str(BASE_DIR), "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
