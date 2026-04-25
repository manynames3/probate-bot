from __future__ import annotations

import os
import threading
from types import SimpleNamespace

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from probate_bot.config import get_sources
from probate_bot.exporters import write_csv, write_json
from probate_bot.service import sync_leads_from_options
from probate_bot.storage import ensure_database, export_leads, get_summary, list_leads, list_recent_runs


def create_app(db_path: str = "./data/probate.sqlite") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "probate-bot-poc"
    app.config["DB_PATH"] = db_path
    app.config["SYNC_STATE"] = {
        "running": False,
        "message": "Idle",
        "last_result": None,
    }
    ensure_database(db_path)

    @app.get("/")
    def index():
        county_filter = request.args.get("county") or None
        min_score_value = request.args.get("min_score")
        min_score = int(min_score_value) if min_score_value else None

        summary = get_summary(app.config["DB_PATH"])
        recent_runs = list_recent_runs(app.config["DB_PATH"], limit=8)
        recent_leads = list_leads(
            app.config["DB_PATH"],
            limit=50,
            county=county_filter,
            min_score=min_score,
        )
        supported_counties = [source.county for source in get_sources("ga") if source.supported]
        return render_template(
            "index.html",
            summary=summary,
            recent_runs=recent_runs,
            recent_leads=recent_leads,
            county_filter=county_filter or "",
            min_score=min_score_value or "",
            supported_counties=supported_counties,
            sync_state=app.config["SYNC_STATE"],
        )

    @app.post("/sync")
    def trigger_sync():
        sync_state = app.config["SYNC_STATE"]
        if sync_state["running"]:
            flash("A sync is already running.", "warning")
            return redirect(url_for("index"))

        counties = request.form.getlist("county")
        all_convenient = request.form.get("all_convenient") == "on"
        days_back = int(request.form.get("days_back", "1"))
        max_results = int(request.form.get("max_results_per_county", "100"))

        sync_state["running"] = True
        sync_state["message"] = "Sync running"
        sync_state["last_result"] = None

        thread = threading.Thread(
            target=_run_sync_background,
            args=(
                app,
                counties,
                all_convenient,
                days_back,
                max_results,
            ),
            daemon=True,
        )
        thread.start()
        flash("Sync started in the background.", "info")
        return redirect(url_for("index"))

    @app.get("/export/<fmt>")
    def export(fmt: str):
        if fmt not in {"csv", "json"}:
            return redirect(url_for("index"))
        leads = export_leads(app.config["DB_PATH"])
        output_path = f"/tmp/probate-export.{fmt}"
        if fmt == "csv":
            write_csv(leads, output_path)
        else:
            write_json(leads, output_path)
        return send_file(output_path, as_attachment=True, download_name=f"probate-leads.{fmt}")

    return app


def _run_sync_background(app: Flask, counties: list[str], all_convenient: bool, days_back: int, max_results: int) -> None:
    sync_state = app.config["SYNC_STATE"]
    try:
        result = sync_leads_from_options(
            db_path=app.config["DB_PATH"],
            trigger_source="web",
            state="ga",
            counties=counties,
            all_convenient=all_convenient,
            start_date=None,
            end_date=None,
            days_back=days_back,
            date_field="filed",
            headless=True,
            max_results_per_county=max_results,
            use_case="research",
        )
        sync_state["message"] = (
            f"Last sync succeeded: found={result.leads_found}, "
            f"inserted={result.inserted}, updated={result.updated}"
        )
        sync_state["last_result"] = result
    except Exception as exc:
        sync_state["message"] = f"Last sync failed: {exc}"
        sync_state["last_result"] = None
    finally:
        sync_state["running"] = False


def main() -> int:
    app = create_app_from_env()
    namespace = SimpleNamespace(
        host=os.getenv("PROBATE_BOT_HOST", "127.0.0.1"),
        port=int(os.getenv("PROBATE_BOT_PORT", "8000")),
        debug=False,
    )
    app.run(host=namespace.host, port=namespace.port, debug=namespace.debug)
    return 0


def create_app_from_env() -> Flask:
    return create_app(db_path=os.getenv("PROBATE_BOT_DB", "./data/probate.sqlite"))


if __name__ == "__main__":
    raise SystemExit(main())
