import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

import usage_guard
from app.routers import video


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def frame_payload(asset_id=42):
    return {
        "video_asset_id": asset_id,
        "focus": "Pressing",
        "desired_count": 2,
        "frame_times": [12, 24],
        "frame_meta": [{}, {}],
        "frames": [
            "data:image/jpeg;base64,ZmFrZS1mcmFtZS0x",
            "data:image/jpeg;base64,ZmFrZS1mcmFtZS0y",
        ],
    }


def selector_result():
    return {
        "selected_indexes": [0, 1],
        "verified_indexes": [0, 1],
        "candidate_indexes": [],
        "rejected_indexes": [],
        "frame_notes": [],
    }


class VideoFrameSelectionAuthTests(unittest.TestCase):
    @staticmethod
    def request():
        return Request({
            "type": "http",
            "method": "POST",
            "path": "/api/video/select-frames",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        })

    def route_patches(self):
        return (
            patch.object(video, "enforce_rate_limit"),
            patch.object(video, "can_use_feature", return_value={"allowed": True}),
            patch.object(video, "_call_openai_frame_selector", return_value=selector_result()),
            patch.object(video, "validate_selection_result", side_effect=lambda result, *_args: result),
        )

    @staticmethod
    def user(user_id):
        user = {"id": user_id, "email": f"user{user_id}@example.test", "is_active": True, "plan": "owner"}
        return user

    def test_unauthenticated_request_returns_expected_401(self):
        limiter, feature, selector, validator = self.route_patches()
        with limiter, feature, selector, validator:
            with self.assertRaises(HTTPException) as raised:
                video.select_video_frames(
                    video.FrameSelectionRequest(**frame_payload()),
                    self.request(),
                    user=None,
                )

        self.assertEqual(raised.exception.status_code, 401)
        self.assertTrue(raised.exception.detail["login_required"])

    def test_authenticated_owner_request_sends_bearer_and_succeeds(self):
        user = self.user(7)
        with (
            patch.object(usage_guard, "decode_access_token", return_value={"sub": "7"}) as decode,
            patch.object(usage_guard, "get_user_by_id", return_value=user),
        ):
            resolved_user = usage_guard.get_optional_user("Bearer valid-owner-token")

        self.assertEqual(resolved_user["id"], 7)
        decode.assert_called_once_with("valid-owner-token")

        limiter, feature, selector, validator = self.route_patches()
        with (
            limiter,
            feature,
            selector,
            validator,
            patch.object(video, "get_video_asset", return_value={"id": 42, "user_id": 7}),
        ):
            response = video.select_video_frames(
                video.FrameSelectionRequest(**frame_payload()),
                self.request(),
                user=resolved_user,
            )

        self.assertEqual(response["verified_indexes"], [0, 1])

    def test_authenticated_non_owner_cannot_select_frames_for_asset(self):
        limiter, feature, selector, validator = self.route_patches()
        with (
            limiter,
            feature,
            selector,
            validator,
            patch.object(video, "get_video_asset", return_value=None),
        ):
            with self.assertRaises(HTTPException) as raised:
                video.select_video_frames(
                    video.FrameSelectionRequest(**frame_payload()),
                    self.request(),
                    user=self.user(8),
                )

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Video non trovato")

    def test_local_upload_without_persisted_asset_remains_supported(self):
        limiter, feature, selector, validator = self.route_patches()
        payload = frame_payload(asset_id=None)
        with (
            limiter,
            feature,
            selector,
            validator,
            patch.object(video, "get_video_asset") as asset_lookup,
        ):
            response = video.select_video_frames(
                video.FrameSelectionRequest(**payload),
                self.request(),
                user=self.user(7),
            )

        self.assertEqual(response["verified_indexes"], [0, 1])
        asset_lookup.assert_not_called()


class VideoAnalysisAuthFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (FRONTEND / "video.html").read_text(encoding="utf-8")
        cls.experience = (FRONTEND / "js" / "video-experience.js").read_text(encoding="utf-8")

    def test_shared_auth_helper_and_bearer_request_are_used(self):
        self.assertIn('<script src="/js/auth.js?v=10542"></script>', self.page)
        self.assertIn("window.MatchIQAuth.authHeaders", self.page)
        self.assertIn('credentials:"same-origin"', self.page)
        self.assertIn("video_asset_id: currentVideoAssetId || null", self.page)

    def test_duplicate_frame_selection_is_guarded(self):
        self.assertIn("let activeFrameSelectionRequest = null", self.page)
        self.assertIn("if(activeFrameSelectionRequest) return activeFrameSelectionRequest", self.page)
        self.assertIn("activeFrameSelectionRequest = null", self.page)

    def test_error_preserves_workspace_and_does_not_return_to_setup(self):
        self.assertIn("const previousWorkspace = {", self.page)
        self.assertIn("extractedFrames = previousWorkspace.frames", self.page)
        self.assertIn('setView("error",{keepScroll:true})', self.experience)
        self.assertNotIn('if(!safeProject().pipeline || !["failed","cancelled"].includes(pipeline().status)) setView("setup")', self.experience)

    def test_retry_reuses_single_start_operation(self):
        self.assertIn("if(analysisStartPromise) return analysisStartPromise", self.experience)
        self.assertIn("if(state.startError) startAnalysis()", self.experience)

    def test_success_keeps_prepare_to_analyze_transition(self):
        start = self.experience.index("async function runAnalysisStart()")
        end = self.experience.index("function openReport()", start)
        operation = self.experience[start:end]
        processing = operation.index('setView("processing")')
        extraction = operation.index("await window.extractFrames()")
        pipeline = operation.index("await window.MatchIQVideoIntelligence.runPipeline()")
        self.assertLess(processing, extraction)
        self.assertLess(extraction, pipeline)

    def test_canvas_readback_hint_is_local(self):
        self.assertIn('canvas.getContext("2d",{willReadFrequently:true})', self.page)


if __name__ == "__main__":
    unittest.main()
