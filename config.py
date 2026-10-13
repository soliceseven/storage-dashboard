"""Config: demo vs live mode, thresholds, credentials."""

import os

LIVE_MODE = os.environ.get("LIVE_MODE", "false").lower() == "true"

# Health score weights
WEIGHTS = {
    "capacity": 0.40,
    "snapshots": 0.25,
    "s3": 0.20,
    "zoning": 0.15,
}

# Thresholds
CAPACITY_WARN_PCT = 85
SNAPSHOT_MAX_AGE_DAYS = 30

# Per-source live config (clients fall back to mock if unset)
ONTAP_CLUSTER = os.environ.get("ONTAP_CLUSTER")
ONTAP_USER = os.environ.get("ONTAP_USER", "admin")
ONTAP_PASSWORD = os.environ.get("ONTAP_PASSWORD")

S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")

INFINIDAT_HOST = os.environ.get("INFINIDAT_HOST")
INFINIDAT_USER = os.environ.get("INFINIDAT_USER", "admin")
INFINIDAT_PASSWORD = os.environ.get("INFINIDAT_PASSWORD")
