import copy
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.video_intelligence import (
    EvidenceClipRequest,
    EvidenceCreateRequest,
    EvidenceFrameRequest,
    EvidenceLinkRequest,
    EvidenceReviewRequest,
    HalftimeAnalysisRequest,
    ReviewStatus,
    VideoPipelineRequest,
    VideoReportRequest,
)
from app.repositories import video_intelligence_repository
from app.services import (
    video_clip_service,
    video_coach_link_service,
    video_evidence_service,
    video_frame_ranking_service,
    video_halftime_service,
    video_intelligence_engine,
    video_report_service,
)
from app.services.video_segmentation_service import segment_frames


ROOT = Path(__file__).resolve().parents[1]


def base_project(**overrides):
    project = {
        "project_id": "vip_test",
        "video_asset_id": 7,
        "analysis_mode": "analysis",
        "period": "first_half",
        "title": "Primo tempo",
        "pipeline": {"status": "review_ready", "stage": "human_review", "progress": 85, "duration_ms": 2_700_000},
        "segments": [],
        "evidences": [],
        "reports": [],
        "halftime_runs": [],
    }
    project.update(overrides)
    return project


class ProjectStore:
    def __init__(self, project=None):
        self.project = copy.deepcopy(project or base_project())
        self.saves = 0

    def load(self, user_id, asset_id):
        if int(user_id) != 1 or int(asset_id) != 7:
            return None
        return copy.deepcopy(self.project)

    def save(self, user_id, asset_id, project, **kwargs):
        if int(user_id) != 1 or int(asset_id) != 7:
            return None
        self.saves += 1
        self.project = copy.deepcopy(project)
        self.project["video_asset_id"] = int(asset_id)
        self.project["asset_status"] = kwargs.get("status") or "ready"
        return copy.deepcopy(self.project)


def sample_evidence(evidence_id="ev_1", status="pending", timestamp_ms=30_000, confidence=0.8):
    return {
        "evidence_id": evidence_id,
        "project_id": "vip_test",
        "video_id": 7,
        "analysis_mode": "analysis",
        "phase_type": "defensive_line",
        "start_timestamp_ms": max(0, timestamp_ms - 5_000),
        "end_timestamp_ms": timestamp_ms + 5_000,
        "representative_timestamp_ms": timestamp_ms,
        "representative_frame": {"timestamp_ms": timestamp_ms, "tier": "slide_ready", "score": 0.9},
        "clip_reference": {"start_timestamp_ms": timestamp_ms - 5_000, "end_timestamp_ms": timestamp_ms + 5_000},
        "title": "Linea difensiva osservabile",
        "observation": "La linea difensiva è visibile nel fotogramma selezionato.",
        "interpretation": None,
        "motivation": "Campo aperto e più giocatori visibili.",
        "confidence_score": confidence,
        "confidence_label": "high",
        "source_type": "ai_visual_assessment",
        "review_status": status,
        "created_at": "2026-07-14T12:00:00Z",
    }


class SegmentationAndRankingTests(unittest.TestCase):
    def test_set_piece_is_classified_from_declared_metadata(self):
        segments = segment_frames(
            [10_000],
            [{"phase": "Calcio d'angolo offensivo", "confidence": 82}],
            90_000,
        )
        self.assertEqual(segments[0]["phase_type"], "attacking_corner")
        self.assertEqual(segments[0]["representative_timestamp_ms"], 10_000)

    def test_close_timestamps_are_deduplicated_by_quality(self):
        segments = segment_frames(
            [10_000, 10_700, 25_000],
            [{"quality": 20}, {"quality": 80}, {"quality": 50}],
            40_000,
        )
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["representative_timestamp_ms"], 10_700)

    def test_unclassified_phase_has_prudent_confidence(self):
        segments = segment_frames([5_000], [{"confidence": 95}], 20_000)
        self.assertEqual(segments[0]["phase_type"], "unclassified")
        self.assertLessEqual(segments[0]["confidence_score"], 0.35)

    def test_wide_frame_scores_above_closeup_celebration(self):
        wide = video_frame_ranking_service.score_frame(
            {"quality": 90, "camera": "wide tactical", "visible_players": 12},
            "defensive_line",
        )
        closeup = video_frame_ranking_service.score_frame(
            {"quality": 90, "camera": "closeup", "scene": "esultanza", "visible_players": 1},
            "defensive_line",
        )
        self.assertGreater(wide["score"], closeup["score"])
        self.assertEqual(wide["tier"], "slide_ready")
        self.assertEqual(closeup["tier"], "discard")

    def test_rank_segments_assigns_stable_unique_ranks(self):
        ranked = video_frame_ranking_service.rank_segments([
            {"frame_meta": {"quality": 30}, "phase_type": "unclassified", "representative_timestamp_ms": 20_000},
            {"frame_meta": {"quality": 90, "camera": "wide"}, "phase_type": "build_up", "representative_timestamp_ms": 10_000},
        ])
        self.assertEqual(sorted(item["frame_rank"] for item in ranked), [1, 2])
        self.assertEqual(ranked[1]["frame_rank"], 1)


class EvidenceLifecycleTests(unittest.TestCase):
    def test_evidence_clamps_timestamps_and_confidence(self):
        evidence = video_evidence_service.build_evidence(
            base_project(),
            7,
            EvidenceCreateRequest(
                start_timestamp_ms=10_000,
                end_timestamp_ms=20_000,
                representative_timestamp_ms=40_000,
                title="Test",
                observation="Fatto osservabile",
                motivation="Frame reale",
                confidence_score=4,
            ),
        )
        self.assertEqual(evidence["representative_timestamp_ms"], 20_000)
        self.assertEqual(evidence["confidence_score"], 1)
        self.assertEqual(evidence["review_status"], "pending")

    def test_review_correction_is_persisted(self):
        store = ProjectStore(base_project(evidences=[sample_evidence()]))
        with (
            patch.object(video_evidence_service, "load_project", store.load),
            patch.object(video_evidence_service, "save_project", store.save),
        ):
            result = video_evidence_service.review_evidence(
                1,
                7,
                "ev_1",
                1,
                EvidenceReviewRequest(
                    status=ReviewStatus.CORRECTED,
                    title="Titolo corretto",
                    observation="Osservazione corretta dallo staff",
                    user_correction="Correzione manuale",
                ),
            )
        self.assertEqual(result["review_status"], "corrected")
        self.assertEqual(result["title"], "Titolo corretto")
        self.assertEqual(store.saves, 1)

    def test_frame_replacement_accepts_only_extracted_timestamp(self):
        segment = {
            "representative_timestamp_ms": 45_000,
            "frame_index": 2,
            "frame_score": 0.8,
            "frame_tier": "slide_ready",
        }
        store = ProjectStore(base_project(segments=[segment], evidences=[sample_evidence()]))
        with (
            patch.object(video_frame_ranking_service, "load_project", store.load),
            patch.object(video_frame_ranking_service, "save_project", store.save),
        ):
            result = video_frame_ranking_service.replace_evidence_frame(
                1, 7, "ev_1", EvidenceFrameRequest(representative_timestamp_ms=45_000)
            )
            with self.assertRaises(ValueError):
                video_frame_ranking_service.replace_evidence_frame(
                    1, 7, "ev_1", EvidenceFrameRequest(representative_timestamp_ms=99_999)
                )
        self.assertEqual(result["representative_timestamp_ms"], 45_000)
        self.assertEqual(result["review_status"], "corrected")

    def test_clip_reference_is_bounded_and_not_a_fake_file(self):
        clip = video_clip_service.build_clip_reference(7, 10_000, 250_000, 300_000)
        self.assertEqual(clip["duration_ms"], 120_000)
        self.assertFalse(clip["generated_file"])
        self.assertEqual(clip["playback_mode"], "seek_and_stop")
        self.assertEqual(clip["stream_url"], "/api/video/library/7/stream")

    def test_clip_update_rejects_reversed_interval(self):
        store = ProjectStore(base_project(evidences=[sample_evidence()]))
        with patch.object(video_clip_service, "load_project", store.load):
            with self.assertRaises(ValueError):
                video_clip_service.update_evidence_clip(
                    1, 7, "ev_1", EvidenceClipRequest(start_timestamp_ms=20_000, end_timestamp_ms=10_000)
                )


class CoachLinkAndReportTests(unittest.TestCase):
    def test_coach_link_suggestions_are_probable_not_confirmed(self):
        evidence = sample_evidence(timestamp_ms=60_000)
        result = video_coach_link_service.suggest_coach_links(
            1,
            base_project(analysis_mode="coach"),
            [evidence],
            [{"id": "event_1", "minute": 1, "title": "Pressing alto"}],
        )
        suggestion = result["evidences"][0]["link_suggestions"][0]
        self.assertEqual(suggestion["link_type"], "probable")
        self.assertIsNone(result["evidences"][0].get("linked_match_event_id"))

    def test_manual_coach_link_must_belong_to_project_events(self):
        evidence = sample_evidence()
        evidence["link_suggestions"] = [{"id": "event_1"}]
        store = ProjectStore(base_project(evidences=[evidence], coach_context={"events": [{"id": "event_1"}]}))
        with (
            patch.object(video_coach_link_service, "load_project", store.load),
            patch.object(video_coach_link_service, "save_project", store.save),
        ):
            linked = video_coach_link_service.set_evidence_link(
                1, 7, "ev_1", EvidenceLinkRequest(linked_match_event_id="event_1")
            )
            with self.assertRaises(ValueError):
                video_coach_link_service.set_evidence_link(
                    1, 7, "ev_1", EvidenceLinkRequest(linked_match_event_id="foreign")
                )
        self.assertEqual(linked["link_type"], "manual_confirmed")

    def test_report_uses_only_accepted_evidence_and_is_idempotent(self):
        store = ProjectStore(base_project(evidences=[
            sample_evidence("confirmed", "confirmed", 10_000),
            sample_evidence("pending", "pending", 20_000),
            sample_evidence("rejected", "rejected", 30_000),
        ]))
        with (
            patch.object(video_report_service, "load_project", store.load),
            patch.object(video_report_service, "save_project", store.save),
        ):
            first = video_report_service.generate_evidence_report(1, 7, VideoReportRequest())
            second = video_report_service.generate_evidence_report(1, 7, VideoReportRequest())
        self.assertEqual(first["report_id"], second["report_id"])
        self.assertEqual(first["summary"]["accepted_evidences"], 1)
        self.assertEqual(first["summary"]["pending_appendix"], 1)
        self.assertEqual(first["summary"]["rejected_excluded"], 1)

    def test_report_refuses_unreviewed_only_project(self):
        store = ProjectStore(base_project(evidences=[sample_evidence()]))
        with patch.object(video_report_service, "load_project", store.load):
            with self.assertRaises(ValueError):
                video_report_service.generate_evidence_report(1, 7, VideoReportRequest())


class PipelineAndSecurityTests(unittest.TestCase):
    def test_pipeline_is_idempotent_without_client_key(self):
        store = ProjectStore()
        request = VideoPipelineRequest(
            duration_seconds=120,
            frame_times_ms=[10_000, 60_000],
            frame_meta=[
                {"phase": "costruzione dal basso", "quality": 80, "camera": "wide"},
                {"phase": "linea difensiva", "quality": 70, "camera": "wide"},
            ],
        )
        with (
            patch.object(video_intelligence_engine, "load_project", store.load),
            patch.object(video_intelligence_engine, "save_project", store.save),
        ):
            first = video_intelligence_engine.run_pipeline(1, 7, request)
            saves_after_first = store.saves
            second = video_intelligence_engine.run_pipeline(1, 7, request)
        self.assertEqual(first["pipeline"]["last_completed_key"], second["pipeline"]["last_completed_key"])
        self.assertEqual(store.saves, saves_after_first)
        self.assertEqual([item["representative_timestamp_ms"] for item in first["evidences"]], [10_000, 60_000])

    def test_pipeline_persists_recoverable_failure(self):
        store = ProjectStore()
        request = VideoPipelineRequest(duration_seconds=60, frame_times_ms=[10_000])
        with (
            patch.object(video_intelligence_engine, "load_project", store.load),
            patch.object(video_intelligence_engine, "save_project", store.save),
            patch.object(video_intelligence_engine, "segment_frames", return_value=[]),
        ):
            with self.assertRaises(ValueError):
                video_intelligence_engine.run_pipeline(1, 7, request)
        self.assertEqual(store.project["pipeline"]["status"], "failed")
        self.assertEqual(store.project["pipeline"]["error"]["code"], "no_reliable_segments")

    def test_repository_load_is_scoped_by_user(self):
        asset = {"id": 7, "status": "ready", "metadata": {"video_intelligence": base_project()}}
        with patch.object(
            video_intelligence_repository,
            "get_video_asset",
            side_effect=lambda user_id, asset_id: asset if user_id == 1 and asset_id == 7 else None,
        ):
            self.assertIsNotNone(video_intelligence_repository.load_project(1, 7))
            self.assertIsNone(video_intelligence_repository.load_project(2, 7))


class HalftimeAndPwaTests(unittest.TestCase):
    def test_halftime_beta_is_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            access = video_halftime_service.halftime_access({"id": 1, "email": "owner@example.com", "role": "owner"})
        self.assertFalse(access["available"])

    def test_halftime_beta_requires_selected_user(self):
        with patch.dict(os.environ, {"VIDEO_HALFTIME_BETA_ENABLED": "1", "VIDEO_HALFTIME_BETA_USER_IDS": "5"}, clear=True):
            self.assertTrue(video_halftime_service.halftime_access({"id": 5, "email": "beta@example.com"})["available"])
            self.assertFalse(video_halftime_service.halftime_access({"id": 6, "email": "other@example.com"})["available"])

    def test_halftime_prioritizes_five_real_evidences(self):
        evidences = [sample_evidence(f"ev_{index}", "pending", index * 10_000, 0.3 + index / 20) for index in range(1, 8)]
        evidences[-1]["review_status"] = "confirmed"
        store = ProjectStore(base_project(evidences=evidences))
        user = {"id": 1, "email": "beta@example.com", "role": "coach"}
        with (
            patch.dict(os.environ, {"VIDEO_HALFTIME_BETA_ENABLED": "1", "VIDEO_HALFTIME_BETA_USER_IDS": "1"}, clear=True),
            patch.object(video_halftime_service, "load_project", store.load),
            patch.object(video_halftime_service, "save_project", store.save),
        ):
            result = video_halftime_service.generate_halftime_analysis(user, 7, HalftimeAnalysisRequest())
        self.assertEqual(len(result["facts"]), 5)
        self.assertEqual(result["facts"][0]["review_status"], "confirmed")
        self.assertTrue(all(item["timestamp_ms"] > 0 for item in result["facts"]))
        self.assertEqual(len(store.project["halftime_runs"]), 1)

    def test_halftime_rejects_non_first_half_project(self):
        store = ProjectStore(base_project(period="full_match", evidences=[sample_evidence()]))
        user = {"id": 1, "email": "beta@example.com"}
        with (
            patch.dict(os.environ, {"VIDEO_HALFTIME_BETA_ENABLED": "1", "VIDEO_HALFTIME_BETA_USER_IDS": "1"}, clear=True),
            patch.object(video_halftime_service, "load_project", store.load),
        ):
            with self.assertRaises(ValueError):
                video_halftime_service.generate_halftime_analysis(user, 7, HalftimeAnalysisRequest())

    def test_pwa_excludes_private_video_and_api_responses(self):
        worker = (ROOT / "frontend" / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname.startsWith("/api/")', worker)
        for extension in ("pdf", "mp4", "webm", "mov", "avi"):
            self.assertIn(extension, worker)
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v133"', worker)

    def test_video_workspace_exposes_review_and_halftime_controls(self):
        page = (ROOT / "frontend" / "video.html").read_text(encoding="utf-8")
        script = (ROOT / "frontend" / "js" / "video-intelligence.js").read_text(encoding="utf-8")
        for token in ("viHalftimeBtn", "viHalftimePanel", "viConfirmVisibleBtn", "viReportBtn"):
            self.assertIn(token, page)
        self.assertIn("requires_staff_verification", script)
        self.assertIn("prepareProject(false)", script)


if __name__ == "__main__":
    unittest.main()
