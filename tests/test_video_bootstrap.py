import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
VIDEO = (FRONTEND / "video.html").read_text(encoding="utf-8")
EXPERIENCE = (FRONTEND / "js" / "video-experience.js").read_text(encoding="utf-8")
WORKER = (FRONTEND / "service-worker.js").read_text(encoding="utf-8")
NAV_CONFIG = (FRONTEND / "js" / "global-nav-config.js").read_text(encoding="utf-8")


class VideoBootstrapRegressionTests(unittest.TestCase):
    def test_boot_class_is_present_before_first_paint(self):
        self.assertRegex(
            VIDEO[:300],
            r'<html\s+lang="it"\s+class="video-ai-booting">',
        )

    def test_critical_boot_css_precedes_application_css(self):
        critical = VIDEO.index('<style id="videoAiBootCritical">')
        application_css = VIDEO.index('<link rel="stylesheet" href="/css/video-intelligence.css')
        body = VIDEO.index("<body")
        self.assertLess(critical, application_css)
        self.assertLess(critical, body)
        self.assertIn(
            "html.video-ai-booting body > main",
            VIDEO[critical:application_css],
        )

    def test_legacy_application_is_hidden_until_mount(self):
        self.assertIn(
            "html.video-ai-booting body > main",
            VIDEO,
        )
        self.assertIn(
            '<main class="wrap" id="videoAppRoot" aria-busy="true" aria-hidden="true">',
            VIDEO,
        )
        self.assertIn('const hero = document.querySelector(".wrap > .hero")', EXPERIENCE)
        self.assertIn('hero.setAttribute("aria-hidden","true")', EXPERIENCE)

    def test_accessible_neutral_shell_precedes_application(self):
        shell = VIDEO.index('id="videoAiBootShell"')
        app = VIDEO.index('id="videoAppRoot"')
        self.assertLess(shell, app)
        self.assertIn('role="status"', VIDEO[shell - 120:shell + 200])
        self.assertIn('aria-busy="true"', VIDEO[shell - 120:shell + 200])
        self.assertIn('src="/assets/matchiq-logo.png"', VIDEO)

    def test_ready_state_is_only_released_after_mount_and_restore(self):
        mount = EXPERIENCE.index("mountExistingExperience();")
        restore = EXPERIENCE.index(
            "applyExperienceState(window.MatchIQVideoIntelligence?.getExperienceState?.() || {});"
        )
        initial_restore = EXPERIENCE.index(
            "Promise.resolve(window.MatchIQVideoInitialRestore)"
        )
        final_restore = EXPERIENCE.index(
            "applyExperienceState(window.MatchIQVideoIntelligence?.getExperienceState?.() || {});",
            initial_restore,
        )
        ready = EXPERIENCE.index("boot?.ready();", final_restore)
        self.assertLess(mount, restore)
        self.assertLess(restore, initial_restore)
        self.assertLess(initial_restore, final_restore)
        self.assertLess(final_restore, ready)
        self.assertIn(
            "window.MatchIQVideoInitialRestore = refreshVideoHub().then(openSessionFromUrl)",
            VIDEO,
        )
        self.assertIn('root.classList.add("video-ai-ready")', VIDEO)
        self.assertIn('main.removeAttribute("aria-hidden")', VIDEO)

    def test_boot_failure_never_reveals_legacy_markup(self):
        self.assertIn("settled = true;", VIDEO)
        self.assertIn('root.classList.add("video-ai-boot-error")', VIDEO)
        self.assertIn("loading.setAttribute(\"role\",\"alert\")", VIDEO)
        self.assertIn(
            "html.video-ai-boot-error body > main",
            VIDEO,
        )
        self.assertIn("Ricarica Video AI", VIDEO)

    def test_essential_assets_have_real_error_paths(self):
        self.assertRegex(
            VIDEO,
            r'<script src="/js/video-intelligence\.js\?v=10541" onerror="[^"]*MatchIQVideoBoot',
        )
        self.assertRegex(
            VIDEO,
            r'<script src="/js/video-experience\.js\?v=10541" onerror="[^"]*MatchIQVideoBoot',
        )
        self.assertIn("}catch(error){\n    boot?.fail(error);", EXPERIENCE)

    def test_no_artificial_delay_in_bootstrap_adapter(self):
        self.assertNotIn("setTimeout", EXPERIENCE)

    def test_adapter_is_mounted_once(self):
        self.assertEqual(
            VIDEO.count('/js/video-experience.js?v=10541'),
            1,
        )
        self.assertIn('shell.dataset.mounted === "true"', EXPERIENCE)
        self.assertIn('shell.dataset.mounted = "true"', EXPERIENCE)

    def test_current_experience_and_library_contracts_remain_available(self):
        self.assertIn('id="videoExperienceShell"', VIDEO)
        self.assertIn('id="vxProjectsDialog"', VIDEO)
        self.assertIn('id="vxProjectsMount"', VIDEO)
        self.assertIn('window.openLibraryVideo', (FRONTEND / "js" / "video-intelligence.js").read_text(encoding="utf-8"))
        self.assertIn('id="downloadPdfBtn"', VIDEO)
        self.assertIn('id="videoInput"', VIDEO)

    def test_navigation_targets_current_video_route_without_redirect(self):
        self.assertIn('withVersion("/video.html")', NAV_CONFIG)
        self.assertNotIn("video-legacy", NAV_CONFIG.lower())

    def test_pwa_release_precaches_only_current_video_assets(self):
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v141"', WORKER)
        self.assertIn('"/video.html?v=10541"', WORKER)
        self.assertNotIn("10540", "\n".join(
            line for line in WORKER.splitlines()
            if "video" in line.lower()
        ))
        self.assertIn("if(request.mode === \"navigate\")", WORKER)
        self.assertIn("fetch(request)", WORKER)

    def test_bootstrap_has_no_duplicate_ready_dispatch(self):
        boot_source = VIDEO[
            VIDEO.index("window.MatchIQVideoBoot"):
            VIDEO.index("</script>", VIDEO.index("window.MatchIQVideoBoot"))
        ]
        self.assertEqual(
            len(re.findall(r'matchiq:video-ready', boot_source)),
            1,
        )


if __name__ == "__main__":
    unittest.main()
