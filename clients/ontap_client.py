"""
NetApp ONTAP live client. Returns None when not configured, so the caller can use mock data.
Responses match mock_data.get_pools() and mock_data.get_volumes().
"""


import config


def _api():
    if not (config.LIVE_MODE and config.ONTAP_CLUSTER and config.ONTAP_PASSWORD):
        return None
    import requests
    from requests.auth import HTTPBasicAuth

    class Api:
        def __init__(self):
            self.base = f"https://{config.ONTAP_CLUSTER}/api"
            self.auth = HTTPBasicAuth(config.ONTAP_USER, config.ONTAP_PASSWORD)

        def get(self, path, params=None):
            r = requests.get(
                self.base + path,
                auth=self.auth,
                params=params or {},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    return Api()


def get_pools():
    api = _api()
    if not api:
        return None
    aggrs = api.get("/storage/aggregates", {"fields": "name,space"}).get("records", [])
    pools = []
    for a in aggrs:
        sp = a.get("space", {})
        total = (sp.get("block_storage", {}).get("size", 0) or 0) / 1e12
        avail = (sp.get("block_storage", {}).get("available", 0) or 0) / 1e12
        pools.append(
            {
                "name": a.get("name", ""),
                "platform": "NetApp ONTAP",
                "total_tb": round(total, 1),
                "used_tb": round(total - avail, 1),
                "volumes": 0,
            }
        )
    return pools


def get_volumes():
    api = _api()
    if not api:
        return None
    vols = api.get("/storage/volumes", {"fields": "name,svm.name,size,space"}).get(
        "records", []
    )
    out = []
    for v in vols:
        size = v.get("size", 0) or 0
        used = v.get("space", {}).get("used", 0) or 0
        out.append(
            {
                "svm": v.get("svm", {}).get("name", ""),
                "volume": v.get("name", ""),
                "platform": "ONTAP",
                "size_gb": round(size / 1e9, 1),
                "used_pct": round(used / size * 100, 1) if size else 0,
            }
        )
    return out
