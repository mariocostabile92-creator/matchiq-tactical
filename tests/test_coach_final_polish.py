import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read_frontend(relative_path):
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


class CoachFinalPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = read_frontend("coach.html")
        cls.styles = read_frontend("css/coach.css")
        cls.actions = read_frontend("js/coach-actions.js")
        cls.match_day = read_frontend("js/coach-match-day.js")
        cls.feedback = read_frontend("js/coach-match-feedback.js")
        cls.voice = read_frontend("js/coach-voice-actions.js")
        cls.voice_render = read_frontend("js/coach-voice-render.js")
        cls.render = read_frontend("js/coach-render.js")
        cls.worker = read_frontend("service-worker.js")

    def test_01_timer_keeps_match_semantics(self):
        self.assertIn('id="coachLiveClock" role="timer"', self.page)
        self.assertIn("getCoachLiveElapsedSeconds()", self.match_day)

    def test_02_timer_has_stable_readable_digits(self):
        self.assertIn("width:5.25ch", self.styles)
        self.assertIn("font-variant-numeric:tabular-nums", self.styles)
        self.assertIn("white-space:nowrap", self.styles)

    def test_03_primary_command_is_unambiguous(self):
        self.assertIn("AZIONE PRINCIPALE", self.page)
        self.assertIn('id="coachLiveToggle"', self.page)
        for label in ("Avvia timer", "Pausa timer", "Riprendi timer"):
            self.assertIn(label, self.page + self.match_day)

    def test_04_phase_commands_are_grouped(self):
        self.assertIn("CAMBIO FASE", self.page)
        for period in ("1T", "INT", "2T", "REC"):
            self.assertIn(f'data-match-period="{period}"', self.page)

    def test_05_unavailable_commands_are_disabled(self):
        self.assertIn("button.disabled = !hasMatch", self.match_day)
        self.assertIn("resetButton.disabled = !hasMatch || elapsedSeconds <= 0", self.match_day)
        self.assertIn("finishButton.disabled = !hasMatch", self.match_day)

    def test_06_critical_actions_are_visually_separate(self):
        self.assertIn("AZIONI CRITICHE", self.page)
        self.assertIn('class="coach-match-command reset"', self.page)
        self.assertIn('class="coach-match-command danger"', self.page)

    def test_07_feedback_region_is_accessible(self):
        self.assertIn('id="coachEventFeedback"', self.page)
        self.assertIn('role="status" aria-live="polite"', self.page)

    def test_08_event_enters_saving_state(self):
        self.assertIn('target.dataset.feedbackState = "saving"', self.feedback)
        self.assertIn('target.setAttribute("aria-busy", "true")', self.feedback)
        self.assertIn('setButtonMessage(target, "Salvataggio...", "Attendi")', self.feedback)

    def test_09_event_shows_success_state(self):
        self.assertIn('target.dataset.feedbackState = "success"', self.feedback)
        self.assertIn('"\\u2713 Registrato", "Evento salvato"', self.feedback)

    def test_10_event_button_restores_automatically(self):
        self.assertIn("setTimeout(() => restoreButton(target), SUCCESS_MS)", self.feedback)
        self.assertIn("buttonStates.delete(button)", self.feedback)

    def test_11_error_state_reenables_action(self):
        self.assertIn('target.dataset.feedbackState = "error"', self.feedback)
        self.assertIn("target.disabled = false", self.feedback)
        self.assertIn('setButtonMessage(target, "Non salvato", message)', self.feedback)

    def test_12_double_tap_does_not_save_twice(self):
        self.assertIn("LOCK_MS = 900", self.feedback)
        self.assertIn("Tocco doppio ignorato", self.feedback)
        self.assertIn("!window.MatchIQMatchDayGuard.allow", self.actions)

    def test_13_team_events_pass_feedback_button(self):
        self.assertIn("'home',this)", self.page)
        self.assertIn("'away',this)", self.page)
        self.assertIn("feedbackButton", self.actions)

    def test_14_cards_are_not_identified_by_color_only(self):
        self.assertIn("Cartellino giallo</span>", self.page)
        self.assertIn("Cartellino rosso</span>", self.page)
        self.assertIn("coach-live-btn.card-yellow", self.styles)
        self.assertIn("coach-live-btn.card-red", self.styles)

    def test_15_voice_recording_is_visually_obvious(self):
        self.assertIn('data-voice-state="IDLE"', self.page)
        self.assertIn('data-voice-state="RECORDING"', self.styles)
        self.assertIn("coach-voice-mic-indicator", self.page)

    def test_16_voice_duration_uses_real_elapsed_time(self):
        self.assertIn("Date.now() - coachVoiceSession.startedAt", self.voice)
        self.assertIn("setInterval(renderCoachVoiceSession, 500)", self.voice)

    def test_17_voice_stop_and_cancel_remain_available(self):
        self.assertIn("Termina e analizza", self.page)
        self.assertIn("cancelCoachVoiceRecording()", self.page)
        self.assertIn("Annulla", self.page)

    def test_18_voice_processing_is_unambiguous(self):
        self.assertIn('PROCESSING:"Elaborazione..."', self.voice)
        self.assertIn('data-voice-state="PROCESSING"', self.styles)

    def test_19_voice_review_keeps_focus_and_actions(self):
        self.assertIn("focus({preventScroll:true})", self.voice)
        for label in (">Conferma<", ">Modifica<", ">Scarta<"):
            self.assertIn(label, self.voice_render)

    def test_20_bookmark_uses_final_label_and_description(self):
        self.assertIn('>Da rivedere</button>', self.page)
        self.assertIn("Segna questo momento per rivederlo dopo la partita.", self.page)
        self.assertIn("Momento segnato al minuto ${event.minute}.", self.match_day)

    def test_21_bookmark_data_contract_is_unchanged(self):
        self.assertIn('addQuickEvent("da_rivedere"', self.match_day)
        self.assertIn('minute:"live"', self.match_day)
        self.assertIn('source:"match-day-bookmark"', self.match_day)

    def test_22_tactical_groups_keep_required_order(self):
        labels = ["Struttura della squadra", "Fasi di gioco", "Strumenti staff"]
        positions = [self.page.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        for label in ("Linea bassa", "Squadra lunga", "Ampiezza", "Profondita", "Seconda palla", "Transizione", "Uscita lato"):
            self.assertIn(label, self.page)

    def test_23_polish_adds_no_new_network_calls(self):
        for source in (self.match_day, self.feedback, self.voice_render):
            self.assertNotIn("fetch(", source)

    def test_24_network_listeners_are_bound_once(self):
        self.assertIn('dataset.coachNetworkBound === "1"', self.feedback)
        self.assertIn('dataset.coachNetworkBound = "1"', self.feedback)
        self.assertIn('{once:true}', self.feedback)

    def test_25_voice_intervals_are_cleaned_up(self):
        self.assertIn("clearInterval(coachVoiceSession.durationTimer)", self.voice)
        self.assertIn("coachVoiceSession.durationTimer = null", self.voice)
        self.assertLess(self.voice.index("clearInterval(coachVoiceSession.durationTimer)"), self.voice.index("setInterval(renderCoachVoiceSession, 500)"))

    def test_26_reduced_motion_is_respected(self):
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.styles)
        self.assertIn("animation:none !important", self.styles)
        self.assertIn("transition:none !important", self.styles)

    def test_27_touch_targets_support_one_hand_use(self):
        self.assertIn("@media(pointer:coarse)", self.styles)
        self.assertIn("min-height:52px", self.styles)
        self.assertIn("touch-action:manipulation", self.styles)

    def test_28_pwa_safe_areas_and_release_are_current(self):
        self.assertIn("@media(display-mode:standalone)", self.styles)
        self.assertIn("safe-area-inset-left", self.styles)
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v135"', self.worker)
        self.assertIn('/coach.html?v=10534', self.worker)

    def test_29_modified_javascript_is_syntax_valid(self):
        scripts = (
            "js/coach-actions.js", "js/coach-match-day.js", "js/coach-match-feedback.js",
            "js/coach-render.js", "js/coach-voice-actions.js", "js/coach-voice-render.js",
            "service-worker.js",
        )
        for script in scripts:
            result = subprocess.run(
                ["node", "--check", str(FRONTEND / script)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_30_non_match_day_coach_surfaces_remain_present(self):
        for marker in ('id="lineupWorkspace"', 'id="lineupPitch"', 'id="lineupBench"', "Aggiungi pagella", 'id="trainingPlanList"'):
            self.assertIn(marker, self.page)


if __name__ == "__main__":
    unittest.main()
