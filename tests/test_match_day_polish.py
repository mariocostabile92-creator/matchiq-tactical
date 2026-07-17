import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read_frontend(relative_path):
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


class MatchDayPolishTests(unittest.TestCase):
    def test_fifty_four_match_day_acceptance_scenarios(self):
        page = read_frontend("coach.html")
        styles = read_frontend("css/coach.css")
        actions = read_frontend("js/coach-actions.js")
        match_day = read_frontend("js/coach-match-day.js")
        voice = read_frontend("js/coach-voice-actions.js")
        voice_render = read_frontend("js/coach-voice-render.js")
        render = read_frontend("js/coach-render.js")
        report = read_frontend("js/coach-report.js")
        feedback = read_frontend("js/coach-match-feedback.js")
        worker = read_frontend("service-worker.js")

        voice_process = voice.split("async function processCoachVoiceCommand", 1)[1].split(
            "function getCoachVoiceProposalById", 1
        )[0]
        halftime = render.split("function buildCoachHalftimeTalk", 1)[1].split(
            "function buildCoachAssistantQuestions", 1
        )[0]

        checks = [
            # Disciplinary events: 10
            ("home yellow", "Cartellino giallo','GIALLO'" in page and "'home')" in page),
            ("home red", "Cartellino rosso','ROSSO'" in page and "'home')" in page),
            ("away yellow", "Cartellino giallo','GIALLO'" in page and "'away')" in page),
            ("away red", "Cartellino rosso','ROSSO'" in page and "'away')" in page),
            ("four card controls", page.count("addLiveEvent('cartellino'") == 4),
            ("home action count", page.count('data-live-team-action data-team="home"') == 9),
            ("away action count", page.count('data-live-team-action data-team="away"') == 9),
            ("card style not color only", "Cartellino giallo</span>" in page and "Cartellino rosso</span>" in page),
            ("score ignores cards", 'getEventsByType("cartellino"' in report),
            ("duplicate lock", "LOCK_MS = 900" in feedback and "isDuplicate" in actions),

            # Information architecture: 10
            ("observation groups", 'class="coach-observation-groups"' in page),
            ("team structure group", "Struttura della squadra" in page),
            ("situations group", "Fasi di gioco" in page),
            ("staff tools group", "Strumenti staff" in page),
            ("four structure actions", all(x in page for x in ("Linea bassa", "Squadra lunga", "Ampiezza", "Profondita"))),
            ("three situation actions", all(x in page for x in ("Seconda palla", "Transizione", "Uscita lato"))),
            ("voice staff action", "Voice Coach</strong>" in page),
            ("manual note action", "focusCoachManualNote()" in page and "focusManualNote" in match_day),
            ("communication action", "Comunicazione','VOICE'" in page),
            ("observed team context", 'id="eventTeamInput"' in page and "coachTacticalTeamHint" in page),

            # Voice Coach state and review flow: 19
            ("idle state", 'IDLE:"IDLE"' in voice),
            ("recording state", 'RECORDING:"RECORDING"' in voice),
            ("processing state", 'PROCESSING:"PROCESSING"' in voice),
            ("review state", 'REVIEW:"REVIEW"' in voice),
            ("success state", 'SUCCESS:"SUCCESS"' in voice),
            ("error state", 'ERROR:"ERROR"' in voice),
            ("explicit start", "coachVoiceSessionStart" in page and "startCoachVoiceNote()" in page),
            ("explicit stop", "coachVoiceSessionStop" in page and "stopCoachVoiceRecording" in voice),
            ("explicit cancel", "coachVoiceSessionCancel" in page and "cancelCoachVoiceRecording" in voice),
            ("real duration", "Date.now() - coachVoiceSession.startedAt" in voice and "coachVoiceDuration" in page),
            ("continuous recognition", "recognition.continuous = true" in voice),
            ("controlled restart", "startCoachVoiceRecognitionCycle(generation)" in voice and "restartTimer" in voice),
            ("unique segments", "segments.some(item => item.key === key)" in voice),
            ("manual finalization", "Termina e analizza" in page and "finishCoachVoiceRecording" in voice),
            ("no automatic apply", "applyCoachVoiceProposal(" not in voice_process),
            ("review transcript", "coachVoiceTranscriptEditor" in voice_render),
            ("review controls", all(x in voice_render for x in (">Conferma<", ">Modifica<", ">Scarta<"))),
            ("double confirm lock", "proposal.applying" in voice),
            ("background safety", "document.hidden" in voice and "Nessun dato e stato salvato" in voice),

            # Review bookmarks: 6
            ("bookmark control", "Da rivedere" in page and "Segna questo momento per rivederlo dopo la partita." in page),
            ("bookmark optional note", "coachReviewNoteInput" in page),
            ("bookmark event type", 'addQuickEvent("da_rivedere"' in match_day),
            ("bookmark live minute", 'minute:"live"' in match_day),
            ("bookmark origin", 'source:"match-day-bookmark"' in match_day),
            ("event return contract", "return event;" in actions),

            # Halftime factual summary: 5
            ("halftime title", "Riepilogo primo tempo" in page and "Riepilogo primo tempo" in report),
            ("interval only", 'coachState.live?.period || "1T") !== "INT"' in render),
            ("score facts", "Punteggio registrato" in halftime),
            ("event count facts", "Eventi totali" in halftime and "Materiale staff" in halftime),
            ("no tactical advice", all(x not in halftime for x in ("serve piu", "insistiamo", "chiedere piu", "continuare a minacciare"))),

            # PWA, touch and release: 4
            ("touch targets", "@media(pointer:coarse)" in styles and "min-height:48px" in styles),
            ("standalone safe area", "@media(display-mode:standalone)" in styles and "safe-area-inset-bottom" in styles),
            ("pwa cache release", 'const CACHE_NAME = "matchiq-pwa-v141"' in worker),
            ("pwa coach assets", all(x in worker for x in ("/coach.html?v=10534", "/css/coach.css?v=10534", "/js/coach-voice-actions.js?v=10534"))),
        ]

        self.assertEqual(len(checks), 54)
        for name, passed in checks:
            with self.subTest(scenario=name):
                self.assertTrue(passed, name)


if __name__ == "__main__":
    unittest.main()
