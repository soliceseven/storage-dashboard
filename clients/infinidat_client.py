"""
INFINIDAT InfiniBox live client. Returns None when not configured, so the caller can use mock data.
"""

import config


def get_pools():
    if not (config.LIVE_MODE and config.INFINIDAT_HOST and config.INFINIDAT_PASSWORD):
        return None
    import requests

    base = f"https://{config.INFINIDAT_HOST}/api/rest"
    r = requests.post(
        f"{base}/users/login",
        json={"user": config.INFINIDAT_USER, "password": config.INFINIDAT_PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    headers = {"Authorization": f"Bearer {r.json()['result']['auth_token']}"}

    pools = requests.get(
        f"{base}/pools",
        headers=headers,
        params={"fields": "name,size,free"},
        timeout=30,
    ).json()["result"]
    out = []
    for pl in pools:
        size = (pl.get("size", 0) or 0) / 1e12
        free = (pl.get("free", 0) or 0) / 1e12
        out.append(
            {
                "name": pl.get("name", ""),
                "platform": "INFINIDAT InfiniBox",
                "total_tb": round(size, 1),
                "used_tb": round(size - free, 1),
                "volumes": 0,
            }
        )
    requests.post(f"{base}/users/logout", headers=headers, timeout=10)
    return out
