"""Three focused smoke checks. Run: python verify_game.py

Uses SDL's dummy display, temporary career files and real game input handlers.
This is not a timed human playtest.
"""

import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from salmon_open_world import SalmonOpenWorld
from salmon_shift import HeldKeys, INTERIOR_TASKS, LOADING_SPOT, TASKS, VALUE_POINTS


class GameChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(pygame.quit)
        root = Path(self.temp.name)
        self.real_music = pygame.mixer.music
        music_patch = patch("pygame.mixer.music", autospec=True)
        self.music = music_patch.start()
        self.music.get_pos.return_value = -1
        self.addCleanup(music_patch.stop)
        self.game = SalmonOpenWorld(root / "world.json", root / "legacy.json")

    def press(self, key):
        self.game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.game._handle_event(pygame.event.Event(pygame.KEYUP, key=key))

    def frames(self, count):
        for _ in range(count):
            self.game._update(1 / 30)

    def screenshot(self, name):
        output = Path(__file__).parent / "verification-output"
        output.mkdir(exist_ok=True)
        for _ in range(24):
            self.game._draw()  # Settle the camera without advancing the simulation.
        pygame.image.save(self.game.canvas, str(output / f"{name}.png"))

    def walk(self, points):
        g = self.game
        for target in points:
            for _ in range(600):
                position = (g.interior_x, g.interior_y) if g.inside_hatchery else (g.player_x, g.player_y)
                if math.dist(position, target) < 8:
                    break
                dx, dy = target[0] - position[0], target[1] - position[1]
                g.held_keys = set()
                if abs(dx) > 4:
                    g.held_keys.add(pygame.K_d if dx > 0 else pygame.K_a)
                if abs(dy) > 4:
                    g.held_keys.add(pygame.K_s if dy > 0 else pygame.K_w)
                g._update(1 / 30)
            else:
                self.fail(f"Walking approach blocked at {g._task()[0]}: {target}")
        g.held_keys.clear()

    def hold(self, key, frames, extra=None):
        self.game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        if extra:
            self.game.held_keys.add(extra)
        self.frames(frames)
        self.game._handle_event(pygame.event.Event(pygame.KEYUP, key=key))
        if extra:
            self.game.held_keys.discard(extra)

    def do_task(self):
        g, task = self.game, self.game._task()
        points = [g._task_target()]
        if task[0] == "lice":
            points = [(2760, 1300), (2432, 1300)] + points
        elif task[0] == "enter":
            points = [(2432, 1090)] + points
        elif task[0] == "harvest":
            points = [(2415, 1300)] + points
        self.walk(points)
        name = task[0]
        if name.startswith("feed"):
            self.press(pygame.K_e)
            if name == "feed1":
                before = g.feed
                self.hold(pygame.K_d, 41)
                self.screenshot("aiming")
                landing, good = g._feed_preview()
                self.assertFalse(good)
                self.press(pygame.K_SPACE)
                self.assertEqual(g.throw_point, landing)
                self.assertFalse(g.feed_spill, "spill resolves at impact")
                self.press(pygame.K_SPACE)
                self.press(pygame.K_e)
                self.assertEqual(g.feed, before - 250, "no second throw in flight")
                self.frames(14)
                self.assertTrue(g.feed_spill)
                self.assertEqual(g.shift_task, 0)
                self.assertEqual(g._shareholder_value(), 0)
                self.screenshot("spill")
                self.press(pygame.K_e)
                self.assertEqual(g.shift_task, 0, "recovery travels down the chute")
                self.frames(14)
                self.assertEqual(g.feed, before - 250, "recovery costs no extra feed")
                self.assertEqual(g._shareholder_value(), 5)
            else:
                for angle in (-1.8, -.851, -.85, 0, .85, .851, 1.8):
                    g.feed_aim = angle
                    self.assertEqual(g._feed_preview()[1], abs(angle) <= .85)
                g.feed_aim = .85 if name == "feed2" else -.85
                landing, good = g._feed_preview()
                self.assertTrue(good)
                self.screenshot("landing-preview")
                self.press(pygame.K_SPACE)
                self.assertEqual(g.throw_point, landing)
                self.assertEqual(g.throw_success, good)
                self.assertEqual(g._task()[0], name, "no credit before impact")
                if name == "feed2":
                    self.hold(pygame.K_d, 12)
                    self.assertEqual(g._task()[0], name)
                    self.frames(2)
                else:
                    self.frames(14)
        elif name == "nets":
            self.press(pygame.K_e)
            self.hold(pygame.K_e, 40, pygame.K_d)
            partial = g.net_progress
            self.frames(10)
            self.assertEqual(g.net_progress, partial, "net pull progress stays")
            self.screenshot("working")
            self.hold(pygame.K_e, 55, pygame.K_d)
        elif name == "lice":
            self.press(pygame.K_e)
            self.hold(pygame.K_SPACE, 31)
            self.frames(10)
            self.assertGreater(g.pump_progress, 1)
            self.hold(pygame.K_SPACE, 31)
        elif name == "fry":
            self.press(pygame.K_SPACE)
            self.press(pygame.K_e)
        elif name == "screen":
            self.press(pygame.K_e)
            self.frames(46)
        elif name == "grade":
            self.press(pygame.K_e)
            count = g.hatchery["count"]
            self.press(pygame.K_SPACE)
            self.assertEqual(g.hatchery["count"], count, "wrong guide loops fish safely")
            self.assertEqual(g._task()[0], "grade")
            self.screenshot("grade-retry")
            self.hold(pygame.K_d, 16)
            self.press(pygame.K_SPACE)
        elif name == "transfer":
            self.press(pygame.K_e)
            self.press(pygame.K_SPACE)
            self.frames(30)
            self.assertEqual(g.hatchery["count"] + g.shift_juveniles, g.transfer_total)
            self.screenshot("transfer-flow")
            self.frames(37)
        elif name == "harvest":
            self.press(pygame.K_e)
            for _ in range(3):
                self.walk([g._task_target()])
                self.press(pygame.K_e)
                self.assertTrue(g.carrying_crate)
                before = (g._shareholder_value(), g.truck_cargo_kg, g.shift_revenue, g.feed, g.fish)
                original_label = g.marketing_label
                self.press(pygame.K_SPACE)
                self.assertNotEqual(g.marketing_label, original_label)
                self.press(pygame.K_SPACE)
                self.assertEqual(g.marketing_label, original_label)
                self.assertEqual(before, (g._shareholder_value(), g.truck_cargo_kg, g.shift_revenue, g.feed, g.fish))
                self.press(pygame.K_SPACE)
                self.walk([g._task_target()])
                self.screenshot("carrying")
                self.press(pygame.K_e)
            self.assertEqual(g.loaded_crates, 3)
        elif task[4]:
            self.hold(pygame.K_e, int(task[4] * 30) + 2)
        else:
            key = pygame.K_SPACE if name.endswith("_weeks") else pygame.K_e
            self.press(key)
        self.assertEqual(g.shift_task, TASKS.index(task) + 1, task[0])
        if g.effect in ("calendar", "grade"):
            if g.effect == "grade":
                self.frames(20)
                self.screenshot("grading-motion")
            self.frames(91)

    def test_shift_progression_and_delivery(self):
        g = self.game
        g.save_path.write_bytes(b'{"cash":12345}')
        g.legacy_path.write_bytes(b'{"cash":67890}')
        career_bytes = (g.save_path.read_bytes(), g.legacy_path.read_bytes())
        self.screenshot("title")
        self.press(pygame.K_RETURN)
        self.press(pygame.K_v)  # Complete the story muted: every payoff is visual too.
        self.screenshot("pens")
        self.assertEqual(g.mode, "shift")
        self.assertFalse(g._shift_complete("transfer"))
        # Outdoor approaches are truly walkable; indoor approaches stay in room.
        for task in TASKS[:19]:
            if task[0] in INTERIOR_TASKS:
                self.assertTrue(42 <= task[2][0] <= 598 and 78 <= task[2][1] <= 308)
            else:
                self.assertTrue(g._walkable(*task[2]), task[0])
        while g._task()[0] != "drive":
            previous = g._task()[0]
            if previous == "transfer":
                # Real gates also reject a corrupted/incomplete batch.
                g.hatchery["vaccinated"] = False
                g.interior_x, g.interior_y = g._task_target()
                self.assertFalse(g._shift_complete("transfer"))
                g.hatchery["vaccinated"] = True
            self.do_task()
            score = g._shareholder_value()
            self.assertEqual(score, sum(VALUE_POINTS.get(t[0], 0) for t in TASKS[:g.shift_task]))
            self.assertFalse(g._shift_complete(previous), "duplicate task")
            self.assertEqual(g._shareholder_value(), score)
            if previous in ("nets", "lice", "vaccine", "grade", "alevins", "feed1", "feed2", "feed3", "eggs", "exit"):
                self.frames(30)
                self.screenshot(previous)
        self.assertEqual(g.week, 8)
        self.assertEqual(g.fish, 666)
        self.assertEqual(g.shift_juveniles, 9364)
        self.assertEqual(g.hatchery["feed_kg"], 250)
        self.assertEqual(g.truck_cargo_kg, 1202.4)
        self.assertEqual(g.shift_care, {"Fed", "Cleaned", "Treated"})
        # Help is repeatable, safe, and does not advance the objective.
        task_index = g.shift_task
        self.press(pygame.K_h)
        self.assertTrue(g._walkable(g.player_x, g.player_y))
        self.assertEqual(g.shift_task, task_index)
        self.assertFalse(g.action_release)
        # Pause/focus loss cannot run the simulation or keep a held action.
        elapsed = g.shift_elapsed
        self.press(pygame.K_ESCAPE)
        self.frames(30)
        self.assertEqual(g.shift_elapsed, elapsed)
        self.press(pygame.K_RETURN)
        g._handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.frames(30)
        self.assertEqual(g.shift_elapsed, elapsed)
        g._handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.press(pygame.K_RETURN)
        # Enter through the ordinary input handler and drive the actual physics.
        g.player_x, g.player_y = g.truck_x + 32, g.truck_y
        self.press(pygame.K_e)
        self.assertTrue(g.in_truck)
        self.assertFalse(g.shift_driving_joke, "entering must not erase the loading line")
        self.screenshot("delivery")
        self.press(pygame.K_SPACE)
        self.assertGreater(g.honk_seconds, 0)
        self.assertIn("Questionable scoop", g._shift_review())
        # Three recoverable wrong-turn bumps: real collision response, no cargo loss.
        for _ in range(3):
            g.truck_x, g.truck_y, g.truck_heading, g.truck_speed = 2718, 1192, -math.pi / 2, 100
            g._update(.05)
            self.assertEqual(g.truck_cargo_kg, 1202.4)
            g.held_keys.clear()
            self.frames(31)
            self.press(pygame.K_h)
        self.assertEqual(g.shift_bumps, 3)
        self.assertIn("Ambitious parking", g._shift_review())
        for wx, wy in ((2800, 1320), (2992, 1540), (3115, 1720), (3230, 1800), (3260, 1910)):
            for _ in range(1200):
                distance = math.dist((g.truck_x, g.truck_y), (wx, wy))
                if distance < 25:
                    break
                angle = math.atan2(wx - g.truck_x, -(wy - g.truck_y))
                error = (angle - g.truck_heading + math.pi) % math.tau - math.pi
                held = set()
                if abs(error) > .04:
                    held.add(pygame.K_d if error > 0 else pygame.K_a)
                if g.truck_speed < 85:
                    held.add(pygame.K_w)
                g.held_keys = held
                g._update(1 / 30)
            else:
                self.fail(f"Delivery route blocked at {(wx, wy)}")
        g.held_keys = {pygame.K_s}
        for _ in range(30):
            if g.truck_speed <= 10:
                break
            g._update(1 / 30)
        g.held_keys.clear()
        self.assertTrue(g._task_near())
        self.assertTrue(g.shift_driving_joke, "the radio joke plays after driving starts")
        self.press(pygame.K_h)
        self.assertEqual((g.truck_x, g.truck_y), LOADING_SPOT)
        self.assertEqual(g.truck_cargo_kg, 1202.4)
        # Return to the already-verified unloading approach to finish the check.
        g.truck_x, g.truck_y = 3260, 1910
        self.press(pygame.K_e)
        self.assertEqual(g._task()[0], "stamp")
        self.frames(25)
        self.screenshot("receiving")
        self.frames(30)
        self.press(pygame.K_h)
        self.assertTrue(g._task_near())
        self.screenshot("manifest")
        self.press(pygame.K_e)
        self.assertEqual(g._task()[0], "stamp", "human signature is not approval")
        self.press(pygame.K_SPACE)
        self.frames(30)
        self.screenshot("authorization")
        self.press(pygame.K_e)
        self.assertEqual(g._task()[0], "done")
        self.assertEqual(g._shareholder_value(), 100)
        self.assertAlmostEqual(g.shift_revenue, 10100.16)
        self.assertEqual(g.truck_cargo_kg, 0)
        self.assertEqual(g.fish, 666)
        self.assertFalse(g._shift_complete("stamp"))
        self.frames(40)  # Let the one-shot stamp and gull badge reveal finish.
        self.screenshot("receipt")
        pygame.display.set_mode((960, 600), pygame.RESIZABLE)
        self.screenshot("receipt-resized")
        pygame.image.save(g.window, str(Path(__file__).parent / "verification-output" / "window-resized.png"))
        self.press(pygame.K_RETURN)
        self.assertEqual(g.shift_task, 0)
        self.assertEqual(g.fish, 1000)
        self.assertEqual(g._shareholder_value(), 0)
        self.assertFalse(g.marketing_label)
        self.assertEqual((g.save_path.read_bytes(), g.legacy_path.read_bytes()), career_bytes)

    def test_short_shift_never_touches_career_files(self):
        g = self.game
        self.assertTrue(g.music_playing, "a random song starts on the title")
        self.assertEqual(len(g.music_tracks), 5)
        self.music.play.assert_called_once_with()
        self.music.set_volume.assert_called_with(.65)
        # Exercise the picker and its keyboard controls on the real event path.
        self.press(pygame.K_b)
        self.assertTrue(g.album_open)
        while g.album_choice:
            self.press(pygame.K_UP)
        self.press(pygame.K_RETURN)
        self.assertEqual(g.music_index, 0)
        self.assertFalse(g.album_open, "choosing a song returns to the title")
        self.press(pygame.K_b)
        self.screenshot("album-title")
        for _ in range(8):
            previous = g.music_index
            g._handle_event(pygame.event.Event(g.music_end_event))
            self.assertNotEqual(g.music_index, previous)
        self.press(pygame.K_b)
        calls = self.music.play.call_count
        track = g.music_index
        g.save_path.write_bytes(b'{"format":1,"cash":12345}')
        g.legacy_path.write_bytes(b'{"cash":67890}')
        before = (g.save_path.read_bytes(), g.legacy_path.read_bytes())
        g._start_mode("shift")
        self.assertEqual(g.music_index, track)
        self.assertEqual(self.music.play.call_count, calls, "mode resets keep the stream")
        elapsed, task = g.shift_elapsed, g.shift_task
        self.press(pygame.K_b)
        self.frames(30)
        self.assertEqual(g.shift_elapsed, elapsed)
        self.assertEqual(g.shift_task, task)
        self.assertFalse(g.music_paused, "browsing lets the player listen")
        self.press(pygame.K_e)
        self.press(pygame.K_ESCAPE)
        self.assertFalse(g.held_keys)
        self.assertFalse(g.shift_paused)
        # Clicking a song returns to a moving, active game with music playing.
        self.press(pygame.K_b)
        row = g._album_row(0)
        g._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                         pos=(row.centerx * 2, row.centery * 2)))
        self.assertFalse(g.album_open)
        self.assertTrue(g.music_playing)
        self.assertFalse(g.music_paused)
        x, clock = g.player_x, g.shift_elapsed
        self.hold(pygame.K_d, 3)
        self.assertGreater(g.player_x, x)
        self.assertGreater(g.shift_elapsed, clock)
        self.press(pygame.K_ESCAPE)
        self.assertTrue(g.music_paused)
        self.press(pygame.K_b)
        self.assertFalse(g.music_paused, "album preview also works from pause")
        self.press(pygame.K_b)
        self.assertTrue(g.shift_paused)
        self.assertTrue(g.music_paused)
        self.press(pygame.K_RETURN)
        self.assertFalse(g.music_paused)
        self.press(pygame.K_ESCAPE)
        self.press(pygame.K_b)
        self.press(pygame.K_RETURN)
        self.assertFalse(g.album_open, "keyboard selection closes the picker too")
        self.assertFalse(g.shift_paused, "choosing a song resumes a paused shift")
        self.assertFalse(g.music_paused)
        g._handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(g.music_paused)
        g._handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(g.music_paused, "shift still awaits Resume")
        self.press(pygame.K_RETURN)
        self.assertFalse(g.music_paused)
        self.press(pygame.K_v)
        self.assertTrue(g.audio_muted)
        self.music.set_volume.assert_called_with(0)
        g._handle_event(pygame.event.Event(g.music_end_event))
        self.music.set_volume.assert_called_with(0)
        g._start_mode("shift")
        self.assertTrue(g.audio_muted, "mute persists for this session")
        self.press(pygame.K_v)
        self.assertFalse(g.audio_muted)
        with patch("pygame.mixer.Sound") as effects:
            for cue in ("stamp", "horn", "outdoor", "corporate", "splash"):
                g._play_cue(cue)
            effects.assert_not_called()
        # Click Stop in a resized, letterboxed window, then ignore stale ends.
        self.press(pygame.K_b)
        pygame.display.set_mode((1000, 700), pygame.RESIZABLE)
        g.album_choice = len(g.music_tracks) + 1
        self.screenshot("album-resized")
        pygame.image.save(g.window, str(Path(__file__).parent / "verification-output" / "album-window.png"))
        row = g._album_row(g.album_choice)
        click = (round(row.centerx * 1.5625), round(row.centery * 1.5625 + 37.5))
        g._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click))
        self.assertFalse(g.music_playing)
        calls = self.music.play.call_count
        g._handle_event(pygame.event.Event(g.music_end_event))
        self.assertEqual(self.music.play.call_count, calls)
        self.press(pygame.K_ESCAPE)
        g._start_mode("shift")
        self.assertFalse(g.music_playing, "Stop survives a mode reset")
        # Whispers starts immediately; the full video waits for 15 song seconds.
        self.press(pygame.K_b)
        self.press(pygame.K_UP)  # Video is directly above Stop Music.
        self.press(pygame.K_RETURN)
        self.assertTrue(g.video_open)
        self.assertAlmostEqual(g.video_frame_time, 0, places=3)
        self.assertEqual(g.music_tracks[g.music_index].stem, "Whispers_of_a_Dusk_Breeze")
        self.music.play.assert_called_with()
        self.assertEqual(g.video_image.get_size(), (640, 360))
        self.screenshot("superstar-music-intro")
        pygame.image.save(g.window, str(Path(__file__).parent / "verification-output" / "superstar-window.png"))
        elapsed, task = g.shift_elapsed, g.shift_task
        self.press(pygame.K_SPACE)
        self.frames(30)
        self.assertEqual(g.video_elapsed, 0)
        self.assertTrue(g.music_paused)
        self.press(pygame.K_SPACE)
        g._handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.frames(30)
        self.assertEqual(g.video_elapsed, 0)
        self.assertTrue(g.music_paused)
        g._handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertFalse(g.music_paused)
        self.frames(35)
        self.assertEqual(g.video_frame_time, 0, "intro must not advance the picture")
        self.music.get_pos.return_value = 14999
        g._update(1 / 30)
        self.assertEqual(g.video_frame_time, 0)
        self.music.get_pos.return_value = 15000
        g._update(1 / 30)
        self.assertEqual(g.video_frame_time, 0, "video starts from the beginning at 15 seconds")
        self.screenshot("superstar-video-start")
        self.music.get_pos.return_value = 17000
        g._update(1 / 30)
        self.assertAlmostEqual(g.video_frame_time, 2, places=3, msg="video follows soundtrack minus 15 seconds")
        self.music.get_pos.return_value = -1
        self.screenshot("superstar-playing")
        self.press(pygame.K_ESCAPE)
        self.assertFalse(g.video_open)
        self.assertIsNone(g.video_container)
        self.assertTrue(g.album_open)
        self.assertTrue(g.music_playing)
        self.assertEqual((g.shift_elapsed, g.shift_task), (elapsed, task))
        # Complete the 15-second intro and the full 60-second video.
        self.press(pygame.K_RETURN)
        self.assertTrue(g.video_open)
        self.frames(2252)
        self.assertFalse(g.video_open)
        self.assertTrue(g.music_playing, "Whispers continues after the video")
        self.assertIsNone(g.video_container)
        self.assertEqual((g.shift_elapsed, g.shift_task), (elapsed, task))
        with patch("av.open", side_effect=FileNotFoundError("missing video")):
            self.press(pygame.K_RETURN)
        self.assertFalse(g.video_open)
        self.assertIn("unavailable", g.video_error)
        self.press(pygame.K_RETURN)
        self.assertTrue(g.video_open)
        g._handle_event(pygame.event.Event(pygame.QUIT))
        self.assertIsNone(g.video_container, "closing the game releases the MP4")
        self.assertEqual((g.save_path.read_bytes(), g.legacy_path.read_bytes()), before)
        g._start_mode("shift")
        # Bad files are skipped; one remaining track repeats, none means silence.
        with patch.object(self.music, "load", side_effect=[pygame.error("bad MP3"), None]):
            g._play_song(0)
        self.assertIn(0, g.music_failed)
        self.assertTrue(g.music_playing)
        g.music_failed = set(range(len(g.music_tracks))) - {g.music_index}
        track = g.music_index
        g._handle_event(pygame.event.Event(g.music_end_event))
        self.assertEqual(g.music_index, track)
        with patch.object(self.music, "load", side_effect=pygame.error("bad MP3")):
            g._play_song()
        self.assertFalse(g.music_playing)
        self.assertEqual(g._music_status(), "Music unavailable")
        tracks, g.music_tracks = g.music_tracks, []
        g._play_song()
        self.assertEqual(g._music_status(), "Music unavailable")
        g.music_tracks, g.music_failed = tracks, set()
        g.music_available = False
        g._play_song()
        self.assertFalse(g.music_playing, "no audio device remains playable")
        # Actually decode every supplied MP3 through SDL; this is not listening.
        for path in tracks:
            self.real_music.load(str(path))
            self.real_music.play()
            self.assertTrue(self.real_music.get_busy(), path.name)
        self.real_music.stop()
        for key in (pygame.K_F5, pygame.K_F9):
            self.press(key)
        g.save()
        g._load_saved_or_legacy()
        self.assertEqual(g.fish, 1000)
        # Completion/restart/menu/close all remain in memory.
        g._start_mode("shift")
        g._start_mode("menu")
        g._handle_event(pygame.event.Event(pygame.QUIT))
        self.assertEqual((g.save_path.read_bytes(), g.legacy_path.read_bytes()), before)
        g._start_mode("career")
        self.assertEqual(g.cash, 12345)
        self.press(pygame.K_b)
        cash, clock = g.cash, g.day_clock
        self.press(pygame.K_F5)
        self.frames(30)
        self.assertEqual((g.cash, g.day_clock), (cash, clock))
        self.screenshot("album-career")
        self.press(pygame.K_ESCAPE)

    def test_career_farming_migration_and_movement(self):
        g = self.game
        legacy = {"cash": 500000, "fish": 9000, "average_weight": 1.2,
                  "truck_cargo_kg": 650, "reputation": 23, "loan_debt": 800,
                  "upgrades": {"aeration": 2, "feed_efficiency": 1}}
        raw = json.dumps(legacy).encode()
        g.legacy_path.write_bytes(raw)
        g._start_mode("career")
        self.assertEqual(g.fish, 9000)
        self.assertEqual(g.cash, 500000)
        self.assertEqual(g.upgrades["feed"], 1)
        self.assertEqual(g.truck_cargo_kg, 650)
        g.active_panel = "pens"
        feed = g.feed
        g._select_option(1)
        self.assertEqual(g.feed, feed - 750)
        g._hatchery_action("incubator", 1)
        for _ in range(7):
            g.water = g.oxygen = 100
            g._advance_week()
        self.assertEqual(g.hatchery["stage"], "smolt_ready")
        g._hatchery_action("hatchery_lab", 1)
        g._hatchery_action("grader", 1)
        fish = g.fish
        count = g.hatchery["count"]
        g._hatchery_action("grader", 2)
        self.assertEqual(g.fish, fish + count)
        self.assertEqual(g.hatchery["stage"], "empty")
        g.active_panel = None
        x = g.player_x
        g._move_player(.05, HeldKeys({pygame.K_d}))
        self.assertGreater(g.player_x, x)
        g.truck_x, g.truck_y = LOADING_SPOT
        g._move_truck(.05, HeldKeys({pygame.K_w}))
        self.assertGreater(g.truck_speed, 0)
        g.save()
        cash = g.cash
        g.cash = 0
        g._load_saved_or_legacy()
        self.assertEqual(g.cash, cash)
        self.assertEqual(g.legacy_path.read_bytes(), raw)
        self.press(pygame.K_b)
        self.press(pygame.K_RETURN)
        self.assertFalse(g.album_open, "career play also continues after selection")
        self.assertTrue(g.music_playing)
        before = g.day_clock
        self.frames(2)
        self.assertGreater(g.day_clock, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
