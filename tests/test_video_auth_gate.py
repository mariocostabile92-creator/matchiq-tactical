import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
VIDEO = (FRONTEND / "video.html").read_text(encoding="utf-8")
AUTH = (FRONTEND / "js" / "auth.js").read_text(encoding="utf-8")
EXPERIENCE = (FRONTEND / "js" / "video-experience.js").read_text(encoding="utf-8")
INTELLIGENCE = (FRONTEND / "js" / "video-intelligence.js").read_text(encoding="utf-8")
LOGIN = (FRONTEND / "login.html").read_text(encoding="utf-8")
REGISTER = (FRONTEND / "register.html").read_text(encoding="utf-8")
VERIFY = (FRONTEND / "verify-email.html").read_text(encoding="utf-8")
WORKER = (FRONTEND / "service-worker.js").read_text(encoding="utf-8")
VIDEO_ROUTER = (ROOT / "app" / "routers" / "video.py").read_text(encoding="utf-8")
INTELLIGENCE_ROUTER = (
    ROOT / "app" / "routers" / "video_intelligence.py"
).read_text(encoding="utf-8")
COACH = (FRONTEND / "coach.html").read_text(encoding="utf-8")


class VideoAnonymousGateContractTests(unittest.TestCase):
    def test_gate_is_present_in_video_page(self):
        self.assertIn('id="videoAuthGate"', VIDEO)

    def test_gate_has_required_title(self):
        self.assertIn("Accedi per analizzare una partita", VIDEO)

    def test_gate_has_login_and_registration_actions(self):
        self.assertIn('id="videoAuthLogin"', VIDEO)
        self.assertIn('id="videoAuthRegister"', VIDEO)
        self.assertIn(">Crea account</a>", VIDEO)

    def test_gate_explains_persistent_value(self):
        for label in (
            "Carica una partita",
            "Rivedi gli episodi",
            "Conferma le evidenze",
            "Conserva report e progetti",
        ):
            self.assertIn(label, VIDEO)

    def test_anonymous_state_hides_every_other_video_child(self):
        css = (FRONTEND / "css" / "video-experience.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            ".video-auth-required > :not(.video-auth-gate){display:none!important}",
            css,
        )

    def test_initial_application_is_not_exposed_before_auth_resolution(self):
        self.assertIn(
            '<main class="wrap" id="videoAppRoot" aria-busy="true" aria-hidden="true">',
            VIDEO,
        )
        self.assertIn(
            "window.MatchIQVideoAuthReady = window.MatchIQAuth.validateSession()",
            VIDEO,
        )

    def test_anonymous_gate_is_released_without_showing_workspace(self):
        self.assertIn('main.classList.add("video-auth-required")', VIDEO)
        self.assertIn("if(gate)", VIDEO)
        self.assertIn("gate.hidden = false", VIDEO)

    def test_no_token_skips_session_api_call(self):
        validate = AUTH[AUTH.index("async function validateSession()") :]
        no_token = validate.index(
            'if(!token) return {authenticated:false, reason:"missing"}'
        )
        auth_me = validate.index('fetch("/api/auth/me"')
        self.assertLess(no_token, auth_me)

    def test_archive_restore_waits_for_authenticated_session(self):
        self.assertIn(
            "window.MatchIQVideoInitialRestore = window.MatchIQVideoAuthReady.then(auth =>",
            VIDEO,
        )
        self.assertIn("if(!auth.authenticated)", VIDEO)
        self.assertIn("window.MatchIQVideoBoot.authRequired(auth.reason)", VIDEO)

    def test_intelligence_does_not_mount_or_fetch_before_auth(self):
        auth_check = INTELLIGENCE.index("if(!auth?.authenticated)")
        setup_lookup = INTELLIGENCE.index(
            'document.getElementById("videoIntelligenceSetup")'
        )
        config_fetch = INTELLIGENCE.index("loadHalftimeConfig()")
        self.assertLess(auth_check, setup_lookup)
        self.assertLess(auth_check, config_fetch)

    def test_experience_does_not_mount_before_auth(self):
        auth_check = EXPERIENCE.index("if(!auth?.authenticated)")
        shell_lookup = EXPERIENCE.index(
            'document.getElementById("videoExperienceShell")'
        )
        self.assertLess(auth_check, shell_lookup)


class VideoSafeReturnContractTests(unittest.TestCase):
    def test_return_url_requires_same_origin(self):
        self.assertIn("candidate.origin !== window.location.origin", AUTH)

    def test_protocol_relative_return_is_rejected(self):
        self.assertIn('candidate.pathname.startsWith("//")', AUTH)

    def test_control_characters_are_rejected(self):
        self.assertRegex(AUTH, r"\\u0000-\\u001f\\u007f")

    def test_login_and_register_return_loops_are_rejected(self):
        self.assertIn('["/login.html", "/register.html"]', AUTH)

    def test_auth_pages_use_shared_return_helper(self):
        self.assertIn("window.MatchIQAuth.requestedReturnUrl()", LOGIN)
        self.assertIn("window.MatchIQAuth.requestedReturnUrl()", REGISTER)

    def test_login_consumes_return_only_after_success(self):
        self.assertIn("window.MatchIQAuth.consumeReturnUrl", LOGIN)
        self.assertIn("window.location.href = postAuthDestination()", LOGIN)

    def test_registration_preserves_return_through_verification(self):
        self.assertIn('link.searchParams.set("next",AUTH_RETURN_URL)', REGISTER)
        self.assertIn("verificationDestination(link)", REGISTER)

    def test_email_verification_routes_back_through_login(self):
        self.assertIn('params.has("next")', VERIFY)
        self.assertIn("window.MatchIQAuth.authPageUrl", VERIFY)

    def test_auth_clear_preserves_video_workspace_and_return_state(self):
        clear = AUTH[
            AUTH.index("function clearAuthSession()") :
            AUTH.index("function normalizeReturnUrl")
        ]
        self.assertNotIn("matchiq_video", clear)
        self.assertNotIn("MATCHIQ_AUTH_RETURN_KEY", clear)


class VideoExpiredSessionRecoveryContractTests(unittest.TestCase):
    def test_unauthorized_intelligence_request_dispatches_expiry(self):
        self.assertIn("response.status === 401 || response.status === 403", INTELLIGENCE)
        self.assertIn("matchiq:video-session-expired", INTELLIGENCE)

    def test_legacy_anonymous_retry_was_removed(self):
        analyze = VIDEO[VIDEO.index("async function analyzeVideo()") :]
        self.assertNotIn(
            'headers:{"Content-Type":"application/json","Accept":"application/json"}',
            analyze[: analyze.index("function downloadBase64Pdf")],
        )

    def test_expired_session_copy_confirms_workspace_preservation(self):
        self.assertIn("Il video, il contesto e i fotogrammi restano disponibili", EXPERIENCE)
        self.assertIn("workspace_preserved:true", EXPERIENCE)

    def test_expired_session_has_one_dominant_recovery_action(self):
        self.assertIn('actions.primary.textContent = "Accedi e riprendi"', EXPERIENCE)
        self.assertIn("if(actions.projects) actions.projects.hidden = true", EXPERIENCE)
        self.assertIn("if(actions.setup) actions.setup.hidden = true", EXPERIENCE)

    def test_reauthentication_uses_popup_to_keep_file_in_memory(self):
        self.assertIn('window.open(loginUrl,"matchiq-video-auth"', EXPERIENCE)

    def test_reauthentication_has_same_tab_fallback(self):
        self.assertIn("else window.location.href = loginUrl", EXPERIENCE)

    def test_recovery_observes_token_and_focus_without_polling(self):
        self.assertIn('window.addEventListener("storage"', EXPERIENCE)
        self.assertIn('window.addEventListener("focus",checkAuthRecovery)', EXPERIENCE)
        recovery = EXPERIENCE[
            EXPERIENCE.index("function showSessionExpired") :
            EXPERIENCE.index("function openReport")
        ]
        self.assertNotIn("setInterval", recovery)

    def test_restored_auth_requires_explicit_resume(self):
        self.assertIn('actions.primary.textContent = "Riprendi analisi"', EXPERIENCE)
        self.assertIn('if(action === "resume-auth")', EXPERIENCE)


class VideoBackendAndPwaAuthContractTests(unittest.TestCase):
    def test_analysis_endpoint_rejects_missing_user(self):
        analyze = VIDEO_ROUTER[
            VIDEO_ROUTER.index("def analyze_video_clip") :
            VIDEO_ROUTER.index("def select_video_frames")
        ]
        self.assertIn("if not user:", analyze)
        self.assertIn("status_code=401", analyze)

    def test_frame_selection_endpoint_rejects_missing_user(self):
        selector = VIDEO_ROUTER[
            VIDEO_ROUTER.index("def select_video_frames") :
            VIDEO_ROUTER.index("def list_video_library")
        ]
        self.assertIn("if not user:", selector)
        self.assertIn("status_code=401", selector)

    def test_library_and_upload_endpoints_require_user(self):
        library = VIDEO_ROUTER[VIDEO_ROUTER.index("def list_video_library") :]
        self.assertIn("def list_video_library(user=Depends(require_user))", library)
        upload = library[
            library.index("def upload_video_library_item") :
            library.index("def import_video_library_url")
        ]
        self.assertIn("user=Depends(require_user)", upload)

    def test_video_intelligence_endpoints_require_user(self):
        protected = len(re.findall(r"user=Depends\(require_user\)", INTELLIGENCE_ROUTER))
        self.assertGreaterEqual(protected, 15)
        self.assertNotIn("get_optional_user", INTELLIGENCE_ROUTER)

    def test_backend_ownership_guards_remain_present(self):
        self.assertIn("def _require_owned_video_asset", VIDEO_ROUTER)
        self.assertIn("def _require_owned_video_report", VIDEO_ROUTER)

    def test_pwa_precaches_gate_and_auth_flow(self):
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v144"', WORKER)
        for asset in (
            '"/video.html?v=10543"',
            '"/login.html?v=10543"',
            '"/register.html?v=10543"',
            '"/verify-email.html?v=10543"',
            '"/js/auth.js?v=10543"',
        ):
            self.assertIn(asset, WORKER)

    def test_coach_does_not_receive_video_gate_markup(self):
        self.assertNotIn("videoAuthGate", COACH)
        self.assertNotIn("video-auth-required", COACH)


if __name__ == "__main__":
    unittest.main()
