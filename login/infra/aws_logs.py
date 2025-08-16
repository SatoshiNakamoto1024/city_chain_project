# infra/aws_logs.py
"""
CloudWatch Logs を簡単にクエリする共通サービス
"""
from __future__ import annotations
import boto3, time, datetime, logging
from typing import List, Dict

logger = logging.getLogger(__name__)
logs = boto3.client("logs", region_name="us-east-1")

LOG_GROUP = "/myapp/production"   # <-- 既に作成済みのグループ名に合わせて修正

def run_insights_query(
    query_str: str,
    start: int | datetime.datetime,
    end: int | datetime.datetime,
    limit: int = 100
) -> List[Dict]:
    """
    CloudWatch Logs Insights でクエリを実行し結果を返す
    start/end : epoch millis もしくは datetime
    """
    def _to_ms(t):
        if isinstance(t, (int, float)):
            return int(t)
        return int(t.timestamp() * 1_000)

    start_ms = _to_ms(start)
    end_ms   = _to_ms(end)

    logger.info("Run Insights query: %s", query_str)
    resp = logs.start_query(
        logGroupName=LOG_GROUP,
        startTime=start_ms // 1000,   # API は秒
        endTime=end_ms // 1000,
        queryString=query_str,
        limit=limit,
    )
    query_id = resp["queryId"]

    # ポーリング
    while True:
        out = logs.get_query_results(queryId=query_id)
        if out["status"] in ("Complete", "Failed", "Cancelled"):
            break
        time.sleep(1)

    if out["status"] != "Complete":
        raise RuntimeError(f"Query failed: {out['status']}")

    # [{field, value}…] → dict へ整形
    rows: List[Dict] = []
    for r in out["results"]:
        row = {f["field"]: f["value"] for f in r}
        rows.append(row)
    return rows


def download_log_stream(stream_name: str) -> List[str]:
    """
    1 つの LogStream をダウンロードし、行テキストの list で返す
    """
    events: List[str] = []
    paginator = logs.get_paginator("get_log_events")
    for page in paginator.paginate(
        logGroupName=LOG_GROUP,
        logStreamName=stream_name,
        startFromHead=True,
    ):
        events.extend(e["message"] for e in page["events"])
    return events
