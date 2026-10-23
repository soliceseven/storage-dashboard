# Storage Health Dashboard

A dashboard for enterprise storage health. It shows capacity, snapshots, S3 posture, and FC zoning—the metrics a storage architect monitors day to day.

## Quick start (demo mode)

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

Demo mode uses realistic mock data, so you don't need storage arrays. The development server binds to `0.0.0.0` and enables Flask debug mode in demo mode. Do not expose this server to untrusted networks.

## Live mode

The live clients are in `clients/`. Set `LIVE_MODE=true` and provide credentials through environment variables:

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

`ONTAP_USER` and `INFINIDAT_USER` default to `admin`. ONTAP and INFINIDAT connections use HTTPS with TLS certificate verification enabled. Their certificates must chain to a CA trusted by the client's CA bundle. For a private CA, set `REQUESTS_CA_BUNDLE` for Requests and `AWS_CA_BUNDLE` for boto3 to a CA bundle that includes it. S3 endpoint TLS follows boto3's certificate trust configuration.

Unconfigured or failed live clients use mock data for their respective sources. In live mode, the app fetches only pools (ONTAP and INFINIDAT), ONTAP volumes, and S3 buckets live. Snapshots and FC zones always use mock data. The health score also always uses mock data; it does not score live-source results.

## What it shows

- **Health score** — weighted composite of capacity (40%), snapshots (25%), S3 (20%), and zoning (15%); derived from mock data in both demo and live modes
- **Capacity** — per-pool gauges with an 85% warning threshold
- **Snapshots** — mock-data compliance table that flags entries older than the configured 30-day threshold
- **S3 posture** — each bucket's encryption, versioning, and public-access settings
- **FC zoning** — mock-data findings for empty zones and multi-initiator violations

## Project layout

```
app.py              Flask app and routes
config.py           Demo/live mode, thresholds, and credentials
mock_data.py        Mock data shaped like real API responses
clients/            Live REST API clients, one per platform
templates/          Jinja2 HTML
static/             CSS
```
