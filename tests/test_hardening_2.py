import json
import os
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

import database
import main
from app.routers import video
from app.security.rate_limit import (
    client_ip,
    enforce_rate_limit,
    reset_rate_limits_for_tests,
)


ROOT = Path(__file__).resolve().parents[1]


def make_request(ip="127.0.0.1", headers=None):
    raw_headers = [
        (str(key).lower().encode("latin-1"), str(value).encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": raw_headers,
        "client": (ip, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    })


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "id":
                self.ids.append(value)


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        reset_rate_limits_for_tests()

    def tearDown(self):
        reset_rate_limits_for_tests()

    def test_threshold_identity_and_retry_after(self):
        request = make_request("10.0.0.1")
        enforce_rate_limit(request, "test.login", 2, 60, "coach@example.com")
        enforce_rate_limit(request, "test.login", 2, 60, "coach@example.com")
        with self.assertRaises(HTTPException) as raised:
            enforce_rate_limit(request, "test.login", 2, 60, "coach@example.com")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("Retry-After", raised.exception.headers)
        enforce_rate_limit(request, "test.login", 2, 60, "other@example.com")

    def test_window_resets(self):
        request = make_request("10.0.0.2")
        with patch("app.security.rate_limit.time.monotonic", side_effect=[10.0, 10.1, 71.0]):
            enforce_rate_limit(request, "test.window", 1, 60)
            with self.assertRaises(HTTPException):
                enforce_rate_limit(request, "test.window", 1, 60)
            enforce_rate_limit(request, "test.window", 1, 60)

    def test_proxy_header_is_trusted_only_when_enabled_and_valid(self):
        request = make_request("10.0.0.3", {"x-forwarded-for": "203.0.113.10"})
        with patch.dict(os.environ, {"TRUST_PROXY_HEADERS": "0"}):
            self.assertEqual(client_ip(request), "10.0.0.3")
        with patch.dict(os.environ, {"TRUST_PROXY_HEADERS": "1"}):
            self.assertEqual(client_ip(request), "203.0.113.10")
        invalid = make_request("10.0.0.4", {"x-forwarded-for": "not-an-ip"})
        with patch.dict(os.environ, {"TRUST_PROXY_HEADERS": "1"}):
            self.assertEqual(client_ip(invalid), "10.0.0.4")


class VideoIntegrityTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.database_path = Path(handle.name)
        handle.close()
        self.original_path = database.DB_PATH
        self.original_postgres = database.USE_POSTGRES
        database.DB_PATH = self.database_path
        database.USE_POSTGRES = False
        database.init_db()
        self.owner_id = database.create_user("owner@example.com", "hash", "owner")
        self.other_id = database.create_user("other@example.com", "hash", "owner")
        self.asset_id = database.create_video_asset(
            self.owner_id,
            title="Partita owner",
            source_type="upload",
            rights_confirmed=True,
        )["id"]

    def tearDown(self):
        database.DB_PATH = self.original_path
        database.USE_POSTGRES = self.original_postgres
        try:
            self.database_path.unlink()
        except OSError:
            pass

    def test_cross_user_asset_and_report_are_not_visible(self):
        saved = database.save_video_report(
            self.owner_id,
            title="Report owner",
            payload={"video_asset_id": self.asset_id},
        )
        with self.assertRaises(HTTPException) as asset_error:
            video._require_owned_video_asset(self.other_id, self.asset_id)
        self.assertEqual(asset_error.exception.status_code, 404)
        with self.assertRaises(HTTPException) as report_error:
            video._require_owned_video_report(self.other_id, saved["id"])
        self.assertEqual(report_error.exception.status_code, 404)

    def test_report_idempotency_prevents_duplicate_records(self):
        first = database.save_video_report(
            self.owner_id,
            title="Report",
            payload={"video_asset_id": self.asset_id},
            idempotency_key="request-123",
        )
        second = database.save_video_report(
            self.owner_id,
            title="Report retried",
            payload={"video_asset_id": self.asset_id},
            idempotency_key="request-123",
        )
        self.assertEqual(first["id"], second["id"])
        self.assertFalse(first["deduplicated"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(database.count_video_reports(self.owner_id), 1)

    def test_feedback_is_deduplicated_and_parent_deletion_is_consistent(self):
        report = database.save_video_report(
            self.owner_id,
            title="Report",
            payload={"video_asset_id": self.asset_id},
        )
        first = database.save_video_frame_feedback(
            self.owner_id,
            video_asset_id=self.asset_id,
            report_id=report["id"],
            frame_index=2,
            status="approvato",
            corrected_phase="pressing",
        )
        second = database.save_video_frame_feedback(
            self.owner_id,
            video_asset_id=self.asset_id,
            report_id=report["id"],
            frame_index=2,
            status="approvato",
            corrected_phase="pressing",
        )
        self.assertEqual(first["id"], second["id"])
        self.assertTrue(second["deduplicated"])
        database.delete_video_asset(self.owner_id, self.asset_id)
        updated = database.get_video_report(self.owner_id, report["id"])
        payload = updated.get("payload") or {}
        if isinstance(payload, str):
            payload = json.loads(payload)
        self.assertIsNone(payload.get("video_asset_id"))
        self.assertEqual(database.get_video_frame_feedback(self.owner_id), [])

    def test_deleting_report_removes_its_feedback(self):
        report = database.save_video_report(self.owner_id, title="Report")
        database.save_video_frame_feedback(
            self.owner_id,
            report_id=report["id"],
            frame_index=1,
            status="scartato",
            corrected_phase="",
        )
        self.assertTrue(database.delete_video_report(self.owner_id, report["id"]))
        self.assertEqual(database.get_video_frame_feedback(self.owner_id), [])


class ContractAndFrontendTests(unittest.TestCase):
    def test_scout_live_route_and_openapi_operation_ids_are_unique(self):
        schema = main.app.openapi()
        scout_operations = schema.get("paths", {}).get("/api/scout-live", {})
        self.assertEqual(list(scout_operations), ["get"])
        operation_ids = [
            operation.get("operationId")
            for path in schema.get("paths", {}).values()
            for operation in path.values()
            if isinstance(operation, dict) and operation.get("operationId")
        ]
        self.assertEqual(len(operation_ids), len(set(operation_ids)))

    def test_match_page_has_no_duplicate_ids(self):
        parser = IdCollector()
        parser.feed((ROOT / "frontend" / "match.html").read_text(encoding="utf-8"))
        duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        self.assertEqual(duplicates, [])

    def test_safe_render_blocks_xss_and_unsafe_urls(self):
        source = ROOT / "frontend" / "js" / "safe-render.js"
        script = (
            "global.window={location:{origin:'https://tactical.matchiq.it'}};"
            f"require({json.dumps(str(source))});"
            "const s=window.MatchIQSafe;"
            "if(s.escapeHtml('<script>')!=='&lt;script&gt;') process.exit(2);"
            "if(s.safeUrl('javascript:alert(1)')!=='#') process.exit(3);"
            "if(s.safeUrl('data:text/html,x')!=='#') process.exit(4);"
            "if(s.safeUrl('https://example.com/x')!=='https://example.com/x') process.exit(5);"
        )
        completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_dynamic_renderers_use_shared_safety_helpers(self):
        sources = (ROOT / "frontend" / "js" / "tactical-assistant-sources.js").read_text(encoding="utf-8")
        renderer = (ROOT / "frontend" / "js" / "tactical-assistant-render.js").read_text(encoding="utf-8")
        state = (ROOT / "frontend" / "js" / "tactical-assistant-state.js").read_text(encoding="utf-8")
        self.assertIn("A.safeUrl", sources)
        self.assertIn("textContent", renderer)
        self.assertIn("window.MatchIQSafe", state)

    def test_api_errors_do_not_return_raw_exception_text(self):
        targets = [
            ROOT / "payments.py",
            ROOT / "app" / "routers" / "admin_analytics.py",
            ROOT / "app" / "routers" / "admin_users.py",
            ROOT / "app" / "routers" / "admin_beta.py",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in targets)
        self.assertNotIn("detail=str(e)", combined)
        self.assertNotIn('"reason": str(e)', combined)
        self.assertNotIn('"message": str(e)', combined)

    def test_pwa_does_not_cache_api_responses_and_logout_clears_state(self):
        worker = (ROOT / "frontend" / "service-worker.js").read_text(encoding="utf-8")
        auth_source = (ROOT / "frontend" / "js" / "auth.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname.startsWith("/api/")', worker)
        self.assertIn('request.method !== "GET"', worker)
        self.assertIn('key.startsWith("matchiq_")', auth_source)

    def test_video_ui_guards_double_submit_and_reuses_idempotency_key(self):
        source = (ROOT / "frontend" / "video.html").read_text(encoding="utf-8")
        self.assertIn("analyzeBtn.disabled = true", source)
        self.assertIn("analyzeBtn.disabled = false", source)
        self.assertIn("matchiqVideoAnalysisRequestKey", source)
        self.assertIn("idempotency_key:", source)


if __name__ == "__main__":
    unittest.main()
