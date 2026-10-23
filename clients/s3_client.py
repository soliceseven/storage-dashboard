"""
S3-compatible live client (Cleversafe/IBM COS, Cloudian, AWS S3, MinIO).
Returns None if not configured (caller falls back to mock).
"""


import config


def _error_code(error):
    response = getattr(error, "response", None)
    if not isinstance(response, dict):
        return None
    details = response.get("Error")
    return details.get("Code") if isinstance(details, dict) else None


def get_buckets():
    if not config.LIVE_MODE:
        return None
    import boto3
    from botocore.config import Config as BotoConfig

    session = boto3.Session()
    kw = {"config": BotoConfig(signature_version="s3v4")}
    if config.S3_ENDPOINT_URL:
        kw["endpoint_url"] = config.S3_ENDPOINT_URL
    s3 = session.client("s3", **kw)

    out = []
    for b in s3.list_buckets()["Buckets"]:
        name = b["Name"]
        try:
            s3.get_bucket_encryption(Bucket=name)
            enc = "ENABLED"
        except Exception as error:
            enc = (
                "DISABLED"
                if _error_code(error) == "ServerSideEncryptionConfigurationNotFoundError"
                else "UNKNOWN"
            )
        try:
            ver = s3.get_bucket_versioning(Bucket=name).get("Status", "Suspended")
        except Exception:
            ver = "Unknown"
        try:
            pab = s3.get_public_access_block(Bucket=name)[
                "PublicAccessBlockConfiguration"
            ]
            full = all(
                pab.get(k)
                for k in (
                    "BlockPublicAcls",
                    "BlockPublicPolicy",
                    "IgnorePublicAcls",
                    "RestrictPublicBuckets",
                )
            )
            pab_s = "FULL" if full else "PARTIAL"
        except Exception as error:
            pab_s = (
                "NONE"
                if _error_code(error) == "NoSuchPublicAccessBlockConfiguration"
                else "UNKNOWN"
            )
        issues = []
        if enc == "DISABLED":
            issues.append("no-encryption")
        if ver == "Suspended":
            issues.append("versioning-off")
        if pab_s in ("NONE", "PARTIAL"):
            issues.append("public-access-risk")
        out.append(
            {
                "bucket": name,
                "encryption": enc,
                "versioning": ver,
                "pab": pab_s,
                "issues": issues,
            }
        )
    return out
