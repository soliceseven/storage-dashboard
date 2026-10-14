# Storage Health Dashboard

A single-pane-of-glass dashboard for enterprise storage health — capacity, snapshots, S3 posture, and FC zoning. Built to demo what a storage architect watches day to day.

## Quick start (demo mode)

```bash
pip install flask
python app.py
# Open http://localhost:5000
```

Demo mode uses realistic mock data — no storage arrays required.

## Live mode

Each data source has a client module under `clients/`. Set `LIVE_MODE=true` and provide credentials via environment variables:

```bash
export LIVE_MODE=true
export ONTAP_CLUSTER=cluster01.example.com ONTAP_PASSWORD=...
export S3_ENDPOINT_URL=https://cos.example.com
python app.py
```

| Client | Source | Env vars |
|--------|--------|----------|
| `ontap_client.py` | NetApp ONTAP REST | `ONTAP_CLUSTER`, `ONTAP_USER`, `ONTAP_PASSWORD` |
| `s3_client.py` | S3-compatible (Cleversafe/Cloudian/AWS) | `S3_ENDPOINT_URL`, AWS creds |
| `infinidat_client.py` | INFINIDAT InfiniBox REST | `INFINIDAT_HOST`, `INFINIDAT_PASSWORD` |

Clients gracefully fall back to mock data per-source if credentials are missing.

## What it shows

- **Health score** — weighted composite (capacity 40%, snapshots 25%, S3 20%, zoning 15%)
- **Capacity** — per-pool gauges with 85% warning threshold
- **Snapshots** — compliance table, flags anything past retention
- **S3 posture** — encryption/versioning/public-access per bucket
- **FC zoning** — empty zones and multi-initiator violations

## Project layout

```
app.py              Flask app + routes
config.py           Demo vs live mode, thresholds
mock_data.py        Realistic fake data matching real API shapes
clients/            Live REST API clients (one per platform)
templates/          Jinja2 HTML
static/             CSS
```
