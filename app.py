#!/usr/bin/env python3
"""Flask app for the Storage Health Dashboard. Runs in demo mode by default; set LIVE_MODE=true to use live APIs."""

import config
import mock_data
from clients import infinidat_client, ontap_client, s3_client
from flask import Flask, render_template

app = Flask(__name__)


def _or_mock(live_fn, mock_fn):
    try:
        result = live_fn()
        if result is not None:
            return result, True
    except Exception as e:
        print(f"Live client failed, using mock: {e}")
    return mock_fn(), False


def collect():
    pools, live_pools = _or_mock(
        lambda: (ontap_client.get_pools() or []) + (infinidat_client.get_pools() or []),
        mock_data.get_pools,
    )
    # Use mock pools if live clients return none, so the demo has complete data.
    if live_pools and not pools:
        pools, live_pools = mock_data.get_pools(), False

    volumes, _ = _or_mock(ontap_client.get_volumes, mock_data.get_volumes)
    buckets, live_buckets = _or_mock(s3_client.get_buckets, mock_data.get_buckets)
    snapshots = mock_data.get_snapshots()  # Snapshots currently use mock data; no live client is available.
    zones = mock_data.get_zones()

    score = mock_data.health_score()

    for p in pools:
        p["used_pct"] = (
            round(p["used_tb"] / p["total_tb"] * 100, 1) if p["total_tb"] else 0
        )
        p["status"] = (
            "critical"
            if p["used_pct"] >= 95
            else "warning"
            if p["used_pct"] >= config.CAPACITY_WARN_PCT
            else "ok"
        )

    stale_snaps = [s for s in snapshots if s["age_days"] > config.SNAPSHOT_MAX_AGE_DAYS]
    bad_buckets = [b for b in buckets if b["issues"]]
    bad_zones = [z for z in zones if z["issues"]]

    return {
        "score": score,
        "pools": pools,
        "volumes": volumes,
        "snapshots": snapshots,
        "stale_snaps": stale_snaps,
        "buckets": buckets,
        "bad_buckets": bad_buckets,
        "zones": zones,
        "bad_zones": bad_zones,
        "live_mode": config.LIVE_MODE,
        "live_sources": {"pools": live_pools, "buckets": live_buckets},
    }


@app.route("/")
def dashboard():
    return render_template("dashboard.html", **collect())


@app.route("/health")
def health():
    return {"status": "ok", "live_mode": config.LIVE_MODE}


if __name__ == "__main__":
    print(
        f"Starting in {'LIVE' if config.LIVE_MODE else 'DEMO'} mode — http://localhost:5000"
    )
    app.run(host="0.0.0.0", port=5000, debug=not config.LIVE_MODE)
