"""Flask application for Envanter.

This server serves the compiled front-end so that navigating directly to the
server's IP address displays the login screen handled by the React app. Any
unknown route will be routed to ``index.html`` allowing React Router to manage
client-side navigation.
"""

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token


BASE_DIR = Path(__file__).resolve().parent / "dist"

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
app.config["JWT_SECRET_KEY"] = "change-me"  # TODO: update in production
jwt = JWTManager(app)


@app.post("/api/login")
def login() -> tuple:
    """Authenticate the user and return an access token."""
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if username == "admin" and password == "password":
        token = create_access_token(identity=username)
        return jsonify(token=token), 200
    return jsonify(error="Invalid credentials"), 401


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
