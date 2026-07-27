import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from research.baseline_runner.contracts import (
    SampleBatch,
    SampledCandidate,
    SelectionObservation,
    VideoMetadata,
)
from research.baseline_runner.reports import render_html_report
from research.baseline_runner.runner import BaselineRunConfig, BaselineRunner
from research.baseline_runner.sampler import (
    CurrentPipelineSampler,
    candidate_count_for_focus,
    tactical_frame_label,
)


class FakeSampler:
    def sample(self, video_path, *, focus, desired_count):
        return SampleBatch(
            video=VideoMetadata(
                file_name="match.mp4",
                path=str(Path(video_path)),
                duration_seconds=90.0,
                fps=25.0,
                width=1280,
                height=720,
                frame_count=2250,
            ),
            candidates=(
                SampledCandidate(
                    index=0,
                    timestamp_seconds=30.0,
                    jpeg_bytes=b"jpeg-one",
                    data_url="data:image/jpeg;base64,b25l",
                    local_metadata={"score": 72.0, "label": "campo aperto"},
                ),
                SampledCandidate(
                    index=1,
                    timestamp_seconds=60.0,
                    jpeg_bytes=b"jpeg-two",
                    data_url="data:image/jpeg;base64,dHdv",
                    local_metadata={"score": 54.0, "label": "lettura tattica"},
                ),
            ),
        )


class FakeSelector:
    def select(self, batch, *, focus, desired_count, context):
        return SelectionObservation(
            raw_result={"selected_indexes": [0]},
            validated_result={
                "verified_indexes": [0],
                "candidate_indexes": [],
                "rejected_indexes": [1],
                "frame_notes": {
                    "0": {
                        "detected_label": "Corner",
                        "confidence": 86,
                        "evidence": "Palla ferma e punto di battuta visibili",
                    },
                    "1": {
                        "detected_label": "Replay",
                        "confidence": 31,
                        "reason": "Replay televisivo",
                    },
                },
                "validation_summary": {"verified": 1, "candidates": 0, "rejected": 1},
            },
            ai_seconds=1.25,
            validation_seconds=0.02,
        )


class VisionBaselineRunnerTests(unittest.TestCase):
    def test_current_candidate_count_rules_are_preserved(self):
        self.assertEqual(candidate_count_for_focus("Analisi tattica generale", 6), 24)
        self.assertEqual(candidate_count_for_focus("Pressing", 2), 16)
        self.assertEqual(candidate_count_for_focus("Calcio d'angolo", 6), 44)

    def test_current_local_labels_are_preserved(self):
        self.assertEqual(tactical_frame_label("Corner", 0.1, 0.03, 0.1), "scartato: poco campo")
        self.assertEqual(tactical_frame_label("Corner", 0.4, 0.03, 0.1), "candidato calcio d'angolo")

    def test_sampler_reads_video_metadata_and_extracts_current_candidate_count(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV development dependency not available")

        with tempfile.TemporaryDirectory() as temporary:
            video_path = Path(temporary) / "synthetic.avi"
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                10.0,
                (320, 180),
            )
            self.assertTrue(writer.isOpened())
            for index in range(50):
                image = np.zeros((180, 320, 3), dtype=np.uint8)
                image[:, :] = (35, 125, 45)
                cv2.line(image, (20, 90), (300, 90), (245, 245, 245), 2)
                cv2.circle(image, (40 + index * 3, 80), 4, (245, 245, 245), -1)
                writer.write(image)
            writer.release()

            batch = CurrentPipelineSampler().sample(
                video_path,
                focus="Pressing",
                desired_count=2,
            )

            self.assertEqual(batch.video.file_name, "synthetic.avi")
            self.assertAlmostEqual(batch.video.fps, 10.0, places=1)
            self.assertEqual(batch.video.width, 320)
            self.assertEqual(batch.video.height, 180)
            self.assertEqual(len(batch.candidates), 16)
            self.assertTrue(all(item.jpeg_bytes.startswith(b"\xff\xd8") for item in batch.candidates))
            self.assertTrue(all("score" in item.local_metadata for item in batch.candidates))

    def test_runner_writes_structured_json_html_and_frame_references(self):
        ticks = iter((10.0, 10.1, 10.4, 12.0))
        with tempfile.TemporaryDirectory() as temporary:
            result = BaselineRunner(
                sampler=FakeSampler(),
                selector=FakeSelector(),
                clock=lambda: next(ticks),
                now=lambda: datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc),
                revision=lambda: "abc123def456",
            ).run(
                BaselineRunConfig(
                    video_path=Path("match.mp4"),
                    output_dir=Path(temporary),
                    focus="Corner",
                    desired_count=2,
                )
            )

            payload = json.loads(result.json_path.read_text(encoding="utf-8"))
            html_text = result.html_path.read_text(encoding="utf-8")
            self.assertEqual(payload["schema_version"], "matchiq.ve-001.baseline-report.v1")
            self.assertEqual(payload["video"]["resolution"], "1280x720")
            self.assertEqual(payload["pipeline_statistics"]["frames_analyzed"], 2)
            self.assertEqual(payload["pipeline_statistics"]["candidates_sent_to_openai"], 2)
            self.assertEqual(payload["pipeline_statistics"]["descriptions_generated"], 2)
            self.assertEqual(payload["category_distribution"], {"Corner": 1, "Replay": 1})
            self.assertEqual(payload["candidates"][0]["confidence"]["displayed"], 86)
            self.assertEqual(payload["candidates"][0]["selection_status"], "verified")
            self.assertTrue((Path(temporary) / payload["candidates"][0]["frame_file"]).is_file())
            self.assertIn("MatchIQ Vision Engine - VE-001 Baseline", html_text)
            self.assertIn("Palla ferma e punto di battuta visibili", html_text)
            self.assertIn("OpenAI Frame Selector + app.services.video_taxonomy", html_text)

    def test_html_escapes_pipeline_content(self):
        report = {
            "run": {"processed_at": "2026-07-27", "pipeline_version": "v1<script>"},
            "video": {
                "file_name": "<match>.mp4",
                "duration_seconds": 1,
                "fps": 25,
                "resolution": "1x1",
                "frame_count": 25,
            },
            "pipeline_statistics": {
                "frames_analyzed": 1,
                "candidates_found": 1,
                "candidates_sent_to_openai": 1,
                "descriptions_generated": 1,
                "average_seconds_per_candidate": 1,
            },
            "performance": {
                "frame_extraction_seconds": 0.1,
                "ai_calls_seconds": 0.8,
                "local_validation_seconds": 0.01,
                "total_processing_seconds": 1,
            },
            "category_distribution": {"<Corner>": 1},
            "candidates": [{
                "index": 0,
                "timestamp_label": "00:01",
                "frame_file": "frames/one.jpg",
                "frame_selected": True,
                "category": "<Corner>",
                "selection_status": "verified",
                "confidence": {"displayed": 80, "type": "AI", "origin": "selector"},
                "description": "<unsafe>",
            }],
            "limitations": {"confidence_note": "<note>"},
        }
        document = render_html_report(report)
        self.assertNotIn("<unsafe>", document)
        self.assertIn("&lt;unsafe&gt;", document)
        self.assertNotIn("<script>", document)


if __name__ == "__main__":
    unittest.main()
