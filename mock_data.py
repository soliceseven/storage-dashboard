"""
Mock data shaped like the real API responses.
Swap in live clients by setting LIVE_MODE=true (see clients/).
"""

from datetime import datetime, timedelta, timezone


def _days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def get_pools():
    return [
        {"name": "ontap_prod_01", "platform": "NetApp ONTAP",
         "total_tb": 500, "used_tb": 412, "volumes": 47},
        {"name": "ontap_dr_01", "platform": "NetApp ONTAP",
         "total_tb": 500, "used_tb": 188, "volumes": 23},
        {"name": "infinibox_01", "platform": "INFINIDAT InfiniBox",
         "total_tb": 1000, "used_tb": 671, "volumes": 89},
        {"name": "cos_prod", "platform": "IBM COS (Cleversafe)",
         "total_tb": 2000, "used_tb": 1240, "volumes": 0,
         "buckets": 34},
    ]


def get_volumes():
    return [
        {"svm": "svm_prod", "volume": "vol_oracle_prod_01",
         "platform": "ONTAP", "size_gb": 2048, "used_pct": 91.2},
        {"svm": "svm_prod", "volume": "vol_vmware_datastore_04",
         "platform": "ONTAP", "size_gb": 4096, "used_pct": 87.5},
        {"svm": "svm_prod", "volume": "vol_sql_ag_02",
         "platform": "ONTAP", "size_gb": 1024, "used_pct": 62.1},
        {"svm": "svm_dr", "volume": "vol_oracle_dr_01",
         "platform": "ONTAP", "size_gb": 2048, "used_pct": 41.8},
        {"svm": "-", "volume": "ib_vol_esx_cluster_a",
         "platform": "InfiniBox", "size_gb": 8192, "used_pct": 73.4},
        {"svm": "-", "volume": "ib_vol_backup_staging",
         "platform": "InfiniBox", "size_gb": 16384, "used_pct": 88.9},
    ]


def get_snapshots():
    return [
        {"svm": "svm_prod", "volume": "vol_oracle_prod_01",
         "snapshot": "daily.2026-10-12", "age_days": 1, "size_gb": 48.2},
        {"svm": "svm_prod", "volume": "vol_oracle_prod_01",
         "snapshot": "daily.2026-09-28", "age_days": 15, "size_gb": 51.7},
        {"svm": "svm_prod", "volume": "vol_vmware_datastore_04",
         "snapshot": "weekly.2026-08-20", "age_days": 54, "size_gb": 312.4},
        {"svm": "svm_dr", "volume": "vol_oracle_dr_01",
         "snapshot": "daily.2026-10-13", "age_days": 0, "size_gb": 12.1},
        {"svm": "-", "volume": "ib_vol_backup_staging",
         "snapshot": "manual.before_migration", "age_days": 67, "size_gb": 891.0},
    ]


def get_buckets():
    return [
        {"bucket": "prod-app-data", "encryption": "ENABLED",
         "versioning": "Enabled", "pab": "FULL", "issues": []},
        {"bucket": "prod-db-backups", "encryption": "ENABLED",
         "versioning": "Enabled", "pab": "FULL", "issues": []},
        {"bucket": "legacy-archive-2019", "encryption": "DISABLED",
         "versioning": "Suspended", "pab": "PARTIAL",
         "issues": ["no-encryption", "versioning-off", "public-access-risk"]},
        {"bucket": "dev-scratch", "encryption": "ENABLED",
         "versioning": "Suspended", "pab": "FULL",
         "issues": ["versioning-off"]},
    ]


def get_zones():
    return [
        {"zone": "zone_esx_hba1_infinibox_a1", "members": 2, "issues": []},
        {"zone": "zone_esx_hba2_infinibox_b1", "members": 2, "issues": []},
        {"zone": "zone_oracle_rac1_ontap_a1", "members": 2, "issues": []},
        {"zone": "zone_legacy_decomm", "members": 0,
         "issues": ["empty-zone"]},
        {"zone": "zone_shared_violation", "members": 4,
         "issues": ["multi-initiator"]},
    ]


def health_score():
    """Weighted composite 0-100. Mirrors the scoring in app.py."""
    pools = get_pools()
    cap_scores = []
    for p in pools:
        pct = p["used_tb"] / p["total_tb"] * 100
        cap_scores.append(max(0, 100 - max(0, pct - 70) * 3))
    capacity = sum(cap_scores) / len(cap_scores)

    snaps = get_snapshots()
    stale = sum(1 for s in snaps if s["age_days"] > 30)
    snapshots = max(0, 100 - stale * 20)

    buckets = get_buckets()
    bad = sum(1 for b in buckets if b["issues"])
    s3 = max(0, 100 - bad * 25)

    zones = get_zones()
    zbad = sum(1 for z in zones if z["issues"])
    zoning = max(0, 100 - zbad * 30)

    total = (capacity * 0.40 + snapshots * 0.25 + s3 * 0.20 + zoning * 0.15)
    return {
        "total": round(total, 1),
        "capacity": round(capacity, 1),
        "snapshots": round(snapshots, 1),
        "s3": round(s3, 1),
        "zoning": round(zoning, 1),
    }
