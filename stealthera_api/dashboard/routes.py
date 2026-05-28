from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for


dashboard_bp = Blueprint("dashboard", __name__)


def require_dashboard_token():
    token = current_app.config.get("DASHBOARD_AUTH_TOKEN", "")
    if not token:
        return
    given = request.args.get("token") or request.headers.get("X-Dashboard-Token")
    if given != token:
        abort(401)


@dashboard_bp.get("/")
def home():
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.get("/dashboard")
def dashboard():
    require_dashboard_token()
    data = current_app.store.dashboard()
    return render_template("dashboard.html", data=data)


@dashboard_bp.get("/api/dashboard/summary")
def dashboard_summary():
    require_dashboard_token()
    return jsonify(current_app.store.dashboard())
