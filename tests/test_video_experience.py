import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
SOURCES = {
    "html": (FRONTEND / "video.html").read_text(encoding="utf-8"),
    "experience": (FRONTEND / "js" / "video-experience.js").read_text(encoding="utf-8"),
    "intelligence": (FRONTEND / "js" / "video-intelligence.js").read_text(encoding="utf-8"),
    "css": (FRONTEND / "css" / "video-experience.css").read_text(encoding="utf-8"),
    "intelligence_css": (FRONTEND / "css" / "video-intelligence.css").read_text(encoding="utf-8"),
    "worker": (FRONTEND / "service-worker.js").read_text(encoding="utf-8"),
}


CONTRACT_CASES = [
    ("shell", "html", 'id="videoExperienceShell"'),
    ("shell_label", "html", 'aria-labelledby="vxExperienceTitle"'),
    ("primary_heading", "html", '<h1 id="vxExperienceTitle">'),
    ("start_view", "html", 'id="vxStartView" data-vx-view="start"'),
    ("setup_view", "html", 'id="vxSetupView" data-vx-view="setup"'),
    ("processing_view", "html", 'id="vxProcessingView" data-vx-view="processing"'),
    ("review_view", "html", 'id="vxReviewView" data-vx-view="review"'),
    ("report_view", "html", 'id="vxReportView" data-vx-view="report"'),
    ("error_view", "html", 'id="vxErrorView" data-vx-view="error"'),
    ("projects_dialog", "html", 'id="vxProjectsDialog"'),
    ("upload_keyboard", "html", 'id="vxUploadDropzone" tabindex="0" role="button"'),
    ("upload_mount", "html", 'id="vxUploadInputMount"'),
    ("mode_group", "html", 'class="vx-mode-choice" role="group"'),
    ("mode_pressed", "html", 'data-vx-mode="analysis" aria-pressed="true"'),
    ("advanced_disclosure", "html", 'id="vxAdvancedSettings"'),
    ("start_analysis", "html", 'id="vxStartAnalysisBtn"'),
    ("processing_live", "html", 'data-vx-view="processing" hidden aria-live="polite"'),
    ("processing_bar", "html", 'id="vxProcessingBar"'),
    ("processing_elapsed", "html", 'id="vxProcessingElapsed"'),
    ("review_grid", "html", 'class="vx-review-grid"'),
    ("evidence_region", "html", 'aria-label="Evidenze da revisionare"'),
    ("report_stats", "html", 'id="vxReportStats"'),
    ("report_document", "html", 'id="vxReportDocument"'),
    ("error_alert", "html", 'data-vx-view="error" hidden role="alert"'),
    ("dialog_label", "html", 'aria-labelledby="vxProjectsTitle"'),
    ("project_summary_live", "html", 'id="vxProjectSummary" aria-live="polite"'),
    ("experience_css_asset", "html", '/css/video-experience.css?v=10540'),
    ("experience_js_asset", "html", '/js/video-experience.js?v=10540'),
    ("video_release", "html", 'const APP_VERSION = "10540"'),
    ("mount_guard", "experience", 'shell.dataset.mounted === "true"'),
    ("reuse_video_input", "experience", 'move("vxUploadInputMount",node("videoInput"))'),
    ("reuse_setup", "experience", 'move("vxSetupEngineMount",setup)'),
    ("reuse_player", "experience", 'move("vxPlayerMount",player)'),
    ("reuse_evidence", "experience", 'move("vxEvidenceMount",evidence)'),
    ("enhanced_class", "experience", 'document.body.classList.add("video-experience-enhanced")'),
    ("state_router", "experience", 'function setView(next, options={})'),
    ("sticky_offset", "experience", 'function syncStickyChrome()'),
    ("sticky_scroll", "experience", 'window.addEventListener("scroll",scheduleStickyChrome,{passive:true})'),
    ("step_accessible_state", "experience", 'step.setAttribute("aria-label"'),
    ("step_completed_glyph", "experience", 'completed ? "✓"'),
    ("frame_ranking_stage", "experience", 'frame_ranking:"Ranking frame"'),
    ("elapsed_timer", "experience", 'window.setInterval(updateElapsed,1000)'),
    ("cancel_action", "experience", 'data-project-action="cancel"'),
    ("retry_action", "experience", 'data-project-action="retry"'),
    ("mode_accessibility", "experience", 'button.setAttribute("aria-pressed"'),
    ("dialog_focus_trap", "experience", 'function trapProjectDialogFocus(event)'),
    ("dialog_native", "experience", 'projectDialog.showModal()'),
    ("dialog_focus_restore", "experience", 'projectDialogOpener.focus()'),
    ("drop_data_transfer", "experience", 'const transfer = new DataTransfer()'),
    ("existing_frame_extraction", "experience", 'await window.extractFrames()'),
    ("existing_pipeline", "experience", 'MatchIQVideoIntelligence.runPipeline'),
    ("report_ready_listener", "experience", 'document.addEventListener("matchiq:video-report-ready"'),
    ("report_download_facade", "experience", 'MatchIQVideoIntelligence?.downloadReport'),
    ("project_summary_escape", "experience", '${html(title)}'),
    ("file_to_setup", "experience", 'if(node("videoInput")?.files?.length) setView("setup")'),
    ("reuse_report_button", "experience", 'const button = node("viReportBtn")'),
    ("completed_to_report", "experience", 'setView("report",{keepScroll:true})'),
    ("experience_event", "intelligence", 'new CustomEvent("matchiq:video-experience"'),
    ("report_ready_event", "intelligence", 'new CustomEvent("matchiq:video-report-ready"'),
    ("authenticated_report_pdf", "intelligence", '/reports/${encodeURIComponent(report.report_id)}/pdf'),
    ("pdf_content_type_guard", "intelligence", 'contentType.includes("application/pdf")'),
    ("pdf_signature_guard", "intelligence", 'String.fromCharCode(...bytes.slice(0,4)) !== "%PDF"'),
    ("report_busy_guard", "intelligence", 'if(state.busy) return;'),
    ("queue_selection", "intelligence", 'aria-selected="${item.evidence_id === state.selectedEvidenceId'),
    ("frame_review", "intelligence", '<span>Frame suggerito</span>'),
    ("frame_alternatives", "intelligence", 'alternative disponibili'),
    ("clip_review", "intelligence", '<span>Clip proposta</span>'),
    ("clip_rolls", "intelligence", 'Pre-roll ${preRoll} s / Post-roll ${postRoll} s'),
    ("evidence_previous", "intelligence", 'data-action="previous-evidence"'),
    ("evidence_next", "intelligence", 'data-action="next-evidence"'),
    ("evidence_confirm", "intelligence", 'data-action="confirm">Conferma'),
    ("evidence_correct", "intelligence", 'data-action="correct">Correggi'),
    ("evidence_reject", "intelligence", 'data-action="reject">Scarta'),
    ("media_stack", "intelligence", 'class="vi-media-stack" aria-label="Timeline, frame e clip"'),
    ("primary_review_actions", "intelligence", 'class="vi-card-actions vi-review-decisions"'),
    ("stable_queue_navigation", "intelligence", 'openMoment(item,false,false)'),
    ("desktop_workspace", "css", 'grid-template-columns:minmax(0,1fr) minmax(300px,336px)'),
    ("desktop_evidence_no_nested_scroll", "css", 'max-height:none;\n    overflow:visible;'),
    ("sticky_step_bar", "css", 'top:var(--vx-nav-height);'),
    ("sticky_navbar", "css", '.video-experience-enhanced > .miq-global-nav{position:sticky'),
    ("report_completion", "html", 'class="vx-report-completion" role="status"'),
    ("report_compact_completion", "css", '.vx-report-ready{min-height:auto}'),
    ("tablet_breakpoint", "css", '@media(max-width:1050px)'),
    ("mobile_breakpoint", "css", '@media(max-width:700px)'),
    ("mobile_touch_actions", "css", '.vx-report-actions .btn,.vx-error-actions .btn'),
    ("safe_area", "css", 'env(safe-area-inset-bottom)'),
    ("reduced_motion", "css", '@media(prefers-reduced-motion:reduce)'),
    ("focus_visible", "css", '.vx-shell :focus-visible,.vx-projects :focus-visible'),
    ("pwa_cache", "worker", 'const CACHE_NAME = "matchiq-pwa-v140"'),
    ("pwa_video_entry", "worker", '"/video.html?v=10540"'),
    ("pwa_css_entry", "worker", '"/css/video-experience.css?v=10540"'),
    ("pwa_intelligence_css_entry", "worker", '"/css/video-intelligence.css?v=10540"'),
    ("pwa_js_entry", "worker", '"/js/video-experience.js?v=10540"'),
    ("pwa_intelligence_js_entry", "worker", '"/js/video-intelligence.js?v=10540"'),
    ("pwa_video_privacy", "worker", 'pdf|mp4|webm|mov|avi|mp3|wav|m4a|ogg|csv'),
]


class HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1_count = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "h1":
            self.h1_count += 1


class VideoExperienceRegressionTests(unittest.TestCase):
    def test_single_page_h1(self):
        parser = HeadingParser()
        parser.feed(SOURCES["html"])
        self.assertEqual(parser.h1_count, 1)

    def test_experience_adapter_does_not_duplicate_api_requests(self):
        self.assertNotIn("fetch(", SOURCES["experience"])

    def test_report_download_no_longer_delegates_to_legacy_pdf_button(self):
        self.assertNotIn('if(action === "download") node("downloadPdfBtn")?.click();', SOURCES["experience"])

    def test_report_download_button_starts_disabled_until_pdf_is_ready(self):
        self.assertIn('data-vx-action="download" disabled aria-disabled="true"', SOURCES["html"])

    def test_experience_states_are_unique(self):
        states = re.findall(r'data-vx-view="([a-z]+)"', SOURCES["html"])
        self.assertEqual(states, ["start", "setup", "processing", "review", "report", "error"])


def _contract_test(source_key, needle):
    def test(self):
        self.assertIn(needle, SOURCES[source_key])
    return test


for case_name, source_key, needle in CONTRACT_CASES:
    setattr(
        VideoExperienceRegressionTests,
        f"test_contract_{case_name}",
        _contract_test(source_key, needle),
    )


if __name__ == "__main__":
    unittest.main()
