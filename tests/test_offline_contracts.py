"""Offline contracts for demo data and live-client transformations."""

import sys
import types
import unittest
from unittest.mock import patch

import config
from clients import infinidat_client, ontap_client, s3_client
import mock_data


class MockDataTests(unittest.TestCase):
    def test_mock_collections_are_fresh_and_keep_expected_shape(self):
        pools = mock_data.get_pools()
        pools[0]["name"] = "mutated"

        fresh_pools = mock_data.get_pools()
        self.assertEqual(fresh_pools[0]["name"], "ontap_prod_01")
        self.assertTrue(
            {"name", "platform", "total_tb", "used_tb", "volumes"}
            <= fresh_pools[0].keys()
        )
        self.assertTrue(
            {"svm", "volume", "platform", "size_gb", "used_pct"}
            <= mock_data.get_volumes()[0].keys()
        )

    def test_snapshot_dates_are_utc_aware(self):
        from datetime import datetime, timedelta

        parsed = datetime.fromisoformat(mock_data._days_ago(1))
        self.assertEqual(parsed.utcoffset(), timedelta(0))

    def test_health_score_is_a_weighted_composite_in_range(self):
        score = mock_data.health_score()

        self.assertEqual(set(score), {"total", "capacity", "snapshots", "s3", "zoning"})
        weighted_display_score = (
            score["capacity"] * 0.40
            + score["snapshots"] * 0.25
            + score["s3"] * 0.20
            + score["zoning"] * 0.15
        )
        self.assertAlmostEqual(score["total"], weighted_display_score, delta=0.1)
        self.assertTrue(all(0 <= value <= 100 for value in score.values()))


class S3ErrorClassificationTests(unittest.TestCase):
    def _collect_with_errors(self, errors):
        class FakeS3:
            def list_buckets(self):
                return {"Buckets": [{"Name": "offline-bucket"}]}

            def get_bucket_encryption(self, **kwargs):
                if "encryption" in errors:
                    raise errors["encryption"]
                return {"Rules": []}

            def get_bucket_versioning(self, **kwargs):
                if "versioning" in errors:
                    raise errors["versioning"]
                return {"Status": "Enabled"}

            def get_public_access_block(self, **kwargs):
                if "public_access" in errors:
                    raise errors["public_access"]
                return {
                    "PublicAccessBlockConfiguration": {
                        "BlockPublicAcls": True,
                        "BlockPublicPolicy": True,
                        "IgnorePublicAcls": True,
                        "RestrictPublicBuckets": True,
                    }
                }

        class FakeSession:
            def client(self, *args, **kwargs):
                return FakeS3()

        boto3_module = types.ModuleType("boto3")
        boto3_module.Session = FakeSession
        botocore_module = types.ModuleType("botocore")
        botocore_module.__path__ = []
        botocore_config_module = types.ModuleType("botocore.config")
        botocore_config_module.Config = lambda **kwargs: object()
        modules = {
            "boto3": boto3_module,
            "botocore": botocore_module,
            "botocore.config": botocore_config_module,
        }
        with patch.object(config, "LIVE_MODE", True), \
                patch.object(config, "S3_ENDPOINT_URL", None), \
                patch.dict(sys.modules, modules):
            return s3_client.get_buckets()[0]

    def test_permission_errors_are_unknown_not_negative_findings(self):
        bucket = self._collect_with_errors(
            {
                "encryption": PermissionError("not authorized"),
                "versioning": TimeoutError("request timed out"),
                "public_access": PermissionError("not authorized"),
            }
        )

        self.assertEqual(bucket["encryption"], "UNKNOWN")
        self.assertEqual(bucket["versioning"], "Unknown")
        self.assertEqual(bucket["pab"], "UNKNOWN")
        self.assertEqual(bucket["issues"], [])

    def test_known_missing_encryption_and_public_block_remain_findings(self):
        class FakeClientError(Exception):
            def __init__(self, code):
                self.response = {"Error": {"Code": code}}

        bucket = self._collect_with_errors(
            {
                "encryption": FakeClientError(
                    "ServerSideEncryptionConfigurationNotFoundError"
                ),
                "public_access": FakeClientError(
                    "NoSuchPublicAccessBlockConfiguration"
                ),
            }
        )

        self.assertEqual(bucket["encryption"], "DISABLED")
        self.assertEqual(bucket["pab"], "NONE")
        self.assertEqual(
            set(bucket["issues"]), {"no-encryption", "public-access-risk"}
        )


class ClientOfflineTests(unittest.TestCase):
    def test_live_clients_short_circuit_in_demo_mode(self):
        with patch.object(config, "LIVE_MODE", False):
            self.assertIsNone(ontap_client.get_pools())
            self.assertIsNone(ontap_client.get_volumes())
            self.assertIsNone(infinidat_client.get_pools())
            self.assertIsNone(s3_client.get_buckets())

    def test_ontap_live_request_verifies_tls_certificate(self):
        with patch.object(config, "LIVE_MODE", True), \
                patch.object(config, "ONTAP_CLUSTER", "cluster.example"), \
                patch.object(config, "ONTAP_PASSWORD", "offline-test-password"), \
                patch("requests.get") as request_get:
            request_get.return_value.json.return_value = {"records": []}

            api = ontap_client._api()
            api.get("/storage/aggregates")

        self.assertIs(request_get.call_args.kwargs.get("verify", True), True)

    def test_infinidat_auth_and_api_requests_verify_tls_certificate(self):
        class FakeResponse:
            def __init__(self, result=None):
                self.result = result

            def raise_for_status(self):
                pass

            def json(self):
                return self.result

        login_response = FakeResponse({"result": {"auth_token": "offline-test-token"}})
        logout_response = FakeResponse()
        pools_response = FakeResponse({"result": []})
        with patch.object(config, "LIVE_MODE", True), \
                patch.object(config, "INFINIDAT_HOST", "infinibox.example"), \
                patch.object(config, "INFINIDAT_PASSWORD", "offline-test-password"), \
                patch("requests.post", side_effect=[login_response, logout_response]) as request_post, \
                patch("requests.get", return_value=pools_response) as request_get:
            self.assertEqual(infinidat_client.get_pools(), [])

        self.assertEqual(request_post.call_count, 2)
        self.assertTrue(
            all(call.kwargs.get("verify", True) is True for call in request_post.call_args_list),
            "INFINIDAT login and logout must verify the server certificate",
        )
        self.assertIs(
            request_get.call_args.kwargs.get("verify", True),
            True,
            "INFINIDAT pool API request must verify the server certificate",
        )

    def test_infinidat_pool_request_uses_login_bearer_token(self):
        class FakeResponse:
            def __init__(self, result=None):
                self.result = result

            def raise_for_status(self):
                pass

            def json(self):
                return self.result

        token = "offline-mocked-token"
        with patch.object(config, "LIVE_MODE", True), \
                patch.object(config, "INFINIDAT_HOST", "infinibox.example"), \
                patch.object(config, "INFINIDAT_PASSWORD", "offline-test-password"), \
                patch(
                    "requests.post",
                    side_effect=[
                        FakeResponse({"result": {"auth_token": token}}),
                        FakeResponse(),
                    ],
                ), \
                patch(
                    "requests.get",
                    return_value=FakeResponse({"result": []}),
                ) as request_get:
            infinidat_client.get_pools()

        self.assertEqual(
            request_get.call_args.kwargs["headers"]["Authorization"],
            f"Bearer {token}",
        )

    def test_ontap_records_are_converted_without_network_access(self):
        class FakeApi:
            def __init__(self):
                self.calls = []

            def get(self, path, params):
                self.calls.append((path, params))
                if path == "/storage/aggregates":
                    return {
                        "records": [
                            {
                                "name": "aggr_a",
                                "space": {"block_storage": {"size": 2_500_000_000_000, "available": 1_000_000_000_000}},
                            }
                        ]
                    }
                if path == "/storage/volumes":
                    return {
                        "records": [
                            {
                                "name": "vol_a",
                                "svm": {"name": "svm_a"},
                                "size": 10_000_000_000,
                                "space": {"used": 2_000_000_000},
                            },
                            {"name": "empty", "size": 0, "space": {"used": 0}},
                        ]
                    }
                self.fail(f"Unexpected API path: {path}")

        fake_api = FakeApi()
        with patch.object(ontap_client, "_api", return_value=fake_api):
            pools = ontap_client.get_pools()
            volumes = ontap_client.get_volumes()

        self.assertEqual(pools[0]["total_tb"], 2.5)
        self.assertEqual(pools[0]["used_tb"], 1.5)
        self.assertEqual(volumes[0]["svm"], "svm_a")
        self.assertEqual(volumes[0]["size_gb"], 10.0)
        self.assertEqual(volumes[0]["used_pct"], 20.0)
        self.assertEqual(volumes[1]["used_pct"], 0)
        self.assertEqual(len(fake_api.calls), 2)


if __name__ == "__main__":
    unittest.main()
