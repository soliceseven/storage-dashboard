# Storage Health Dashboard

A single-pane-of-glass dashboard for enterprise storage health — capacity, snapshots, S3 posture, and FC zoning. Built to demo what a storage architect watches day to day.

## Quick start (demo mode)

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

Demo mode uses realistic mock data — no storage arrays required. The development server binds to `0.0.0.0`; demo mode also enables Flask debug mode. Do not expose this server to untrusted networks.

## Live mode

Live clients are under `clients/`. Set `LIVE_MODE=true` and provide credentials via environment variables:

```bash
export LIVE_MODE=true
export ONTAP_CLUSTER=cluster01.example.com ONTAP_USER=admin ONTAP_PASSWORD=...
export INFINIDAT_HOST=infinibox.example.com INFINIDAT_USER=admin INFINIDAT_PASSWORD=...
export S3_ENDPOINT_URL=https://cos.example.com  # optional for AWS S3
python app.py
```

| Client | Source | Env vars |
|--------|--------|----------|
| `ontap_client.py` | NetApp ONTAP REST | `ONTAP_CLUSTER`, `ONTAP_USER`, `ONTAP_PASSWORD` |
| `s3_client.py` | S3-compatible (Cleversafe/Cloudian/AWS) | Optional `S3_ENDPOINT_URL`; AWS credentials from boto3's standard credential chain (for example environment variables, shared credentials/config files, or an instance role) |
| `infinidat_client.py` | INFINIDAT InfiniBox REST | `INFINIDAT_HOST`, `INFINIDAT_USER`, `INFINIDAT_PASSWORD` |

`ONTAP_USER` and `INFINIDAT_USER` default to `admin`. ONTAP and INFINIDAT connections use HTTPS with TLS certificate verification enabled; certificates must chain to a CA trusted by the client's CA bundle. For a private CA, configure Requests with `REQUESTS_CA_BUNDLE` and boto3 with `AWS_CA_BUNDLE` to use a CA bundle that includes it. S3 endpoint TLS follows boto3's certificate trust configuration.

Unconfigured or failed live clients fall back to mock data for their respective live sources. In live mode, only pools (ONTAP and INFINIDAT), ONTAP volumes, and S3 buckets are fetched live. Snapshots and FC zones are always mock data, and the health score is always calculated from mock data; it is not a score of live-source results.

## What it shows

- **Health score** — weighted composite (capacity 40%, snapshots 25%, S3 20%, zoning 15%); currently mock-data-derived in both demo and live modes
- **Capacity** — per-pool gauges with 85% warning threshold
- **Snapshots** — mock-data compliance table, flags entries older than the configured 30-day threshold
- **S3 posture** — encryption/versioning/public-access per bucket
- **FC zoning** — mock-data findings for empty zones and multi-initiator violations

## Project layout

```
app.py              Flask app + routes
config.py           Demo vs live mode, thresholds
mock_data.py        Realistic fake data matching real API shapes
clients/            Live REST API clients (one per platform)
templates/          Jinja2 HTML
static/             CSS
```
