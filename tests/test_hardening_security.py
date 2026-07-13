import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

import payments
import auth
import database
from app.routers.system import create_system_router
from app.security.rate_limit import reset_rate_limits_for_tests
from security import load_jwt_secret


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


class FakeRequest:
    def __init__(self, headers=None, body=b"{}"):
        self.headers = headers or {}
        self._body = body

    async def body(self):
        return self._body


class HardeningSecurityTests(unittest.TestCase):
    def test_webhook_fails_closed_without_secret(self):
        with patch.object(payments, "STRIPE_WEBHOOK_SECRET", ""):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(payments.stripe_webhook(FakeRequest()))
        self.assertEqual(raised.exception.status_code, 503)

    def test_webhook_requires_signature(self):
        with patch.object(payments, "STRIPE_WEBHOOK_SECRET", "whsec_test"):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(payments.stripe_webhook(FakeRequest()))
        self.assertEqual(raised.exception.status_code, 400)

    def test_webhook_uses_verified_event_only(self):
        verified = {"type": "test.event", "data": {"object": {}}}
        with (
            patch.object(payments, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(payments.stripe.Webhook, "construct_event", return_value=verified) as verify,
        ):
            result = asyncio.run(
                payments.stripe_webhook(
                    FakeRequest({"stripe-signature": "signed"}, b"payload")
                )
            )
        self.assertTrue(result["received"])
        verify.assert_called_once_with(
            payload=b"payload",
            sig_header="signed",
            secret="whsec_test",
        )

    def test_jwt_secret_prefers_environment(self):
        configured = "a" * 48
        with patch.dict(os.environ, {"JWT_SECRET_KEY": configured}, clear=True):
            self.assertEqual(load_jwt_secret(), configured)

    def test_jwt_secret_is_strong_and_persistent_without_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_path = Path(directory) / ".jwt_secret"
            with patch.dict(os.environ, {}, clear=True):
                first = load_jwt_secret(str(secret_path))
                second = load_jwt_secret(str(secret_path))
        self.assertGreaterEqual(len(first), 32)
        self.assertEqual(first, second)
        self.assertNotEqual(first, "MATCHIQ_SUPER_SECRET_KEY_CHANGE_THIS")

    def test_sensitive_links_are_hidden_by_default(self):
        auth_source = (ROOT / "auth.py").read_text(encoding="utf-8")
        admin_source = (ROOT / "app" / "routers" / "admin_users.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("PASSWORD_RESET_EXPOSE_LINK", "0")', auth_source)
        self.assertIn('os.getenv("EMAIL_VERIFICATION_EXPOSE_LINK", "0")', auth_source)
        self.assertIn('os.getenv("EMAIL_VERIFICATION_EXPOSE_LINK", "0")', admin_source)

    def test_cache_mutations_require_admin_dependency(self):
        def admin_guard():
            return True

        router = create_system_router(
            live_matches_cache={},
            full_analysis_cache={},
            scout_players_cache={},
            live_matches_cache_seconds=1,
            full_analysis_cache_seconds=1,
            scout_players_cache_seconds=1,
            services_provider=lambda: {},
            admin_dependency=admin_guard,
        )
        protected = {
            route.path: route
            for route in router.routes
            if route.path in {"/api/cache-status", "/api/clear-cache"}
        }
        self.assertEqual(set(protected), {"/api/cache-status", "/api/clear-cache"})
        for route in protected.values():
            self.assertTrue(
                any(dependency.call is admin_guard for dependency in route.dependant.dependencies)
            )

    def test_logout_clears_user_scoped_browser_state(self):
        source = (ROOT / "frontend" / "js" / "auth.js").read_text(encoding="utf-8")
        self.assertIn("function clearSensitiveLocalState()", source)
        self.assertIn('key.startsWith("matchiq_")', source)
        self.assertIn("clearSensitiveLocalState();", source)
        self.assertIn("clearSensitiveLocalState,", source)

    def test_pwa_version_is_consistent_for_hardening_release(self):
        manifest = (ROOT / "frontend" / "manifest.json").read_text(encoding="utf-8")
        worker = (ROOT / "frontend" / "service-worker.js").read_text(encoding="utf-8")
        app_meta = (ROOT / "frontend" / "js" / "app-meta.js").read_text(encoding="utf-8")
        self.assertIn('"/index.html?v=10515"', worker)
        self.assertIn('"start_url": "/index.html?v=10515"', manifest)
        self.assertIn('version: "10515"', app_meta)
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v115"', worker)
        self.assertIn('"/js/auth.js?v=10515"', worker)
        self.assertIn('"/js/safe-render.js?v=10515"', worker)


class AuthenticationFlowTests(unittest.TestCase):
    def setUp(self):
        reset_rate_limits_for_tests()
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.database_path = Path(handle.name)
        handle.close()
        self.original_path = database.DB_PATH
        self.original_postgres = database.USE_POSTGRES
        database.DB_PATH = self.database_path
        database.USE_POSTGRES = False
        database.init_db()

    def tearDown(self):
        reset_rate_limits_for_tests()
        database.DB_PATH = self.original_path
        database.USE_POSTGRES = self.original_postgres
        try:
            self.database_path.unlink()
        except OSError:
            pass

    def register_and_login(self):
        with patch.object(auth, "send_verification_email", return_value=False):
            registered = auth.register(
                auth.RegisterRequest(email="coach@example.com", password="password-forte"),
                make_request(),
            )
        logged = auth.login(
            auth.LoginRequest(email="coach@example.com", password="password-forte"),
            make_request(),
        )
        return registered, logged

    def test_register_login_and_authenticated_session(self):
        registered, logged = self.register_and_login()
        self.assertNotIn("verification_link", registered)
        self.assertTrue(logged["token"])
        current = auth.get_current_user(f'Bearer {logged["token"]}')
        self.assertEqual(current["email"], "coach@example.com")

    def test_invalid_token_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            auth.get_current_user("Bearer token-non-valido")
        self.assertEqual(raised.exception.status_code, 401)

    def test_disabled_user_session_is_rejected(self):
        _, logged = self.register_and_login()
        conn = database.get_connection()
        conn.execute("UPDATE users SET is_active=0 WHERE email=?", ("coach@example.com",))
        conn.commit()
        conn.close()
        with self.assertRaises(HTTPException) as raised:
            auth.get_current_user(f'Bearer {logged["token"]}')
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
