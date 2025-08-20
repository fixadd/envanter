"""Flask application for Envanter.

Provides a minimal API endpoint for user authentication along with placeholder
routes for the main pages of the application so that requesting ``/``,
``/login``, ``/inventory``, ``/licenses`` and ``/logout`` no longer results in
``404`` errors.
"""

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token


app = Flask(__name__)
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


@app.get("/")
def index() -> str:
    """Return a simple home page."""

    return "Home page"


@app.get("/login")
def login_page() -> str:
    """Return a simple login page."""

    return "Login page"


@app.get("/inventory")
def inventory_page() -> str:
    """Return a simple inventory page."""

    return "Inventory page"


@app.get("/licenses")
def licenses_page() -> str:
    """Return a simple licenses page."""

    return "Licenses page"


@app.get("/logout")
def logout_page() -> str:
    """Return a simple logout page."""

    return "Logout page"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
