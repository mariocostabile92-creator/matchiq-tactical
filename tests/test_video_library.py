import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import video_hub


ROOT = Path(__file__).resolve().parents[1]


def asset(asset_id=1, **metadata_overrides):
    metadata = {
        "hub_version": 2,
        "session_type": "official_match",
        "session_date": "2026-07-10",
        "team": "MatchIQ FC",
        "home_team": "MatchIQ FC",
        "away_team": "Rivali",
        "competition": "Campionato",
        "season": "2026/27",
        "archive_state": "active",
        "workflow_state": "to_analyze",
        "tags": ["pressing"],
    }
    metadata.update(metadata_overrides)
    return {
        "id": asset_id,
        "user_id": 7,
        "title": f"Partita {asset_id}",
        "club_name": "MatchIQ FC",
        "category": "Dilettanti",
        "source_type": "upload",
        "source_url": "",
        "file_path": f"/private/{asset_id}.mp4",
        "file_name": f"match-{asset_id}.mp4",
        "mime_type": "video/mp4",
        "size_bytes": 1024,
        "rights_confirmed": True,
        "status": "ready",
        "metadata": metadata,
        "created_at": f"2026-07-{asset_id:02d}T10:00:00+00:00",
        "updated_at": f"2026-07-{asset_id:02d}T11:00:00+00:00",
    }


def intelligence_project(review_status="pending", with_report=False):
    evidence = {
        "evidence_id": "ev_1",
        "review_status": review_status,
        "reviewed_at": "2026-07-10T12:00:00+00:00" if review_status != "pending" else "",
        "representative_timestamp_ms": 25_000,
        "representative_frame": {"frame_index": 3},
        "clip_reference": {"start_timestamp_ms": 20_000, "end_timestamp_ms": 30_000},
        "title": "Pressing alto",
        "observation": "Squadra corta nella meta campo avversaria",
    }
    reports = []
    if with_report:
        reports.append({
            "report_id": "rep_1",
            "status": "ready",
            "generated_at": "2026-07-10T13:00:00+00:00",
            "title": "Report partita",
        })
    return {
        "analysis_mode": "analysis",
        "pipeline": {"status": "review_ready", "stage": "human_review", "progress": 85},
        "evidences": [evidence],
        "reports": reports,
    }


class VideoLibraryProjectionTests(unittest.TestCase):
    def test_review_state_and_lightweight_counts_are_derived(self):
        row = asset(video_intelligence=intelligence_project())
        item = video_hub.public_video_session(row)
        self.assertEqual(item["library_state"], "review")
        self.assertEqual(item["frame_count"], 1)
        self.assertEqual(item["clip_count"], 1)
        self.assertEqual(item["report_state"], "absent")
        self.assertNotIn("file_path", item)

    def test_confirmed_evidence_and_report_make_project_complete(self):
        row = asset(video_intelligence=intelligence_project("confirmed", with_report=True))
        item = video_hub.public_video_session(row)
        self.assertEqual(item["library_state"], "complete")
        self.assertEqual(item["report_state"], "ready")
        self.assertTrue(item["report"]["pdf_ready"])

    def test_legacy_projects_remain_openable_and_are_flagged(self):
        row = asset()
        row["metadata"].pop("hub_version")
        row["metadata"].pop("session_date")
        item = video_hub.public_video_session(row)
        self.assertTrue(item["legacy_project"])
        self.assertTrue(item["incomplete_metadata"])
        self.assertEqual(item["id"], row["id"])


class VideoLibraryQueryTests(unittest.TestCase):
    def test_filters_sorting_and_real_pagination_use_owner_scope(self):
        rows = [asset(index) for index in range(1, 16)]
        rows[4]["source_type"] = "url"
        rows[4]["metadata"]["source_provider"] = "authorized_url"

        def page(user_id, limit=50, offset=0):
            self.assertEqual(user_id, 7)
            return rows[offset:offset + limit]

        with (
            patch.object(video_hub, "count_video_assets", return_value=len(rows)),
            patch.object(video_hub, "get_video_assets", side_effect=page),
        ):
            result = video_hub.list_video_sessions(7, {
                "source": "upload",
                "sort": "oldest",
                "limit": 5,
                "offset": 5,
                "archive_state": "active",
            })

        self.assertEqual(result["total"], 14)
        self.assertEqual(result["count"], 5)
        self.assertTrue(result["has_more"])
        self.assertEqual([item["id"] for item in result["items"]], [7, 8, 9, 10, 11])

    def test_search_indexes_staff_corrections_without_exposing_media(self):
        project = intelligence_project("corrected")
        project["evidences"][0]["user_correction"] = "Pressione orientata sul terzino"
        rows = [asset(1, video_intelligence=project), asset(2)]
        with (
            patch.object(video_hub, "count_video_assets", return_value=2),
            patch.object(video_hub, "get_video_assets", return_value=rows),
        ):
            result = video_hub.list_video_sessions(7, {
                "search": "terzino",
                "limit": 12,
                "archive_state": "active",
            })
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], 1)


class VideoLibraryFrontendContractTests(unittest.TestCase):
    def test_official_name_and_library_controls_are_present(self):
        page = (ROOT / "frontend" / "video.html").read_text(encoding="utf-8")
        self.assertIn("LIBRERIA VIDEO AI", page)
        self.assertIn('id="hubPagination"', page)
        self.assertIn('id="hubReportFilter"', page)
        self.assertIn("downloadLibraryPdf", page)
        self.assertNotIn("VIDEO HUB", page)

    def test_pwa_bypasses_private_api_media_and_pdf(self):
        worker = (ROOT / "frontend" / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname.startsWith("/api/")', worker)
        self.assertIn("pdf|mp4|webm|mov|avi", worker)
        self.assertIn("video-library.css?v=10541", worker)
        self.assertIn('matchiq-pwa-v141', worker)

    def test_premium_library_hierarchy_keeps_existing_actions(self):
        page = (ROOT / "frontend" / "video.html").read_text(encoding="utf-8")
        for marker in (
            "Tutte le analisi, i report e i progetti video del tuo staff",
            "library-primary-action",
            "library-secondary-action",
            "library-utility-action",
            "library-item-primary",
            "library-item-secondary",
            "library-item-facts",
            "library-progress-wrap",
        ):
            self.assertIn(marker, page)
        for handler in (
            "openNewSessionWizard()",
            "focusDeviceUpload()",
            "focusAuthorizedImport()",
            "openLibraryVideo(",
            "openLibraryReport(",
            "downloadLibraryPdf(",
        ):
            self.assertIn(handler, page)

    def test_upload_consents_are_labelled_and_not_preselected(self):
        page = (ROOT / "frontend" / "video.html").read_text(encoding="utf-8")
        self.assertIn('class="library-check" for="libraryRights"', page)
        self.assertIn('class="library-check" for="libraryUrlRights"', page)
        self.assertIn('id="libraryRights" type="checkbox"', page)
        self.assertIn('id="libraryUrlRights" type="checkbox"', page)
        self.assertNotIn('id="libraryRights" type="checkbox" checked', page)
        self.assertNotIn('id="libraryUrlRights" type="checkbox" checked', page)

    def test_empty_state_and_responsive_contract_are_present(self):
        page = (ROOT / "frontend" / "video.html").read_text(encoding="utf-8")
        css = (ROOT / "frontend" / "css" / "video-library.css").read_text(encoding="utf-8")
        self.assertIn("Il tuo primo progetto Video AI parte da qui.", page)
        self.assertIn("Importa link autorizzato", page)
        self.assertIn("@media (max-width: 820px)", css)
        self.assertIn("@media (max-width: 560px)", css)
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("body.video-experience-enhanced:has(#vxProjectsDialog[open])", css)

    def test_accessible_filter_and_action_menus(self):
        page = (ROOT / "frontend" / "video.html").read_text(encoding="utf-8")
        css = (ROOT / "frontend" / "css" / "video-library.css").read_text(encoding="utf-8")
        self.assertIn('aria-controls="hubFilterPanel"', page)
        self.assertIn('aria-controls="libraryMenu${Number(item.id)}"', page)
        self.assertIn('role="menuitem"', page)
        self.assertIn(":focus-visible", css)


if __name__ == "__main__":
    unittest.main()
