# admin/admin_blueprint/admin_logs_bp.py
from __future__ import annotations
import io, csv, datetime
from flask import Blueprint, request, jsonify, render_template, send_file, g
from werkzeug.exceptions import BadRequest
import sys, os, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from infra.aws_logs import run_insights_query, download_log_stream

admin_logs_bp = Blueprint("admin_logs_bp", __name__,
                          url_prefix="/admin/logs",
                          template_folder="../templates")

# ==========================
# HTML ページ
# ==========================
@admin_logs_bp.get("/")
def logs_home():
    """
    検索フォーム + 最近 1h のログを表示
    """
    end   = datetime.datetime.utcnow()
    start = end - datetime.timedelta(hours=1)
    rows  = run_insights_query(
        query_str="fields @timestamp, @message | sort @timestamp desc",
        start=start,
        end=end,
        limit=100,
    )
    return render_template("admin_logs.html", rows=rows)


# ==========================
# API: Insights クエリ
# ==========================
@admin_logs_bp.post("/query")
def api_query_logs():
    data = request.get_json(silent=True) or {}
    query   = data.get("query")
    hours   = int(data.get("hours", 1))
    if not query:
        raise BadRequest("query is required")

    end   = datetime.datetime.utcnow()
    start = end - datetime.timedelta(hours=hours)
    rows  = run_insights_query(query, start, end, limit=1000)
    return jsonify({"rows": rows})


# ==========================
# API: LogStream ダウンロード
# ==========================
@admin_logs_bp.get("/download")
def api_download_stream():
    stream = request.args.get("stream")
    if not stream:
        raise BadRequest("stream param required")

    lines = download_log_stream(stream)

    # CSV として返却
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["line"])
    for ln in lines:
        w.writerow([ln])
    buf.seek(0)

    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{stream}.csv",
    )
