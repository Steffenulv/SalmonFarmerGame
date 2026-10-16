"""The disposable salmon shift: a task list, a few counters, and wet paperwork.

This mixin uses the existing game's world, hatchery, movement and truck. There is
deliberately no shift save format, quest framework, or separate simulation.
"""

import math
from pathlib import Path
import random
import pygame


# id, objective, approach position, control, hold seconds. Interior positions
# are the existing hatchery stations, not another map or navigation system.
TASKS = (
    ("feed1", "Feed the mature salmon: spot 1 of 3", (2476, 1287), "E: take scoop", 0),
    ("feed2", "Equal pellets! Feed spot 2 of 3", (2576, 1287), "E: take scoop", 0),
    ("feed3", "Feed spot 3 of 3. Ignore the committee.", (2676, 1287), "E: take scoop", 0),
    ("nets", "Pull the fouling out of the net", (2720, 1185), "E: grip maintenance pole", 3),
    ("lice", "Treat sea lice. Evict the tiny tenants.", (2432, 1185), "E: connect treatment hose", 2),
    ("enter", "Raise REPLACEMENT salmon at the hatchery", (2370, 1063), "E: enter hatchery", 0),
    ("eggs", "Incubator: receive fertilized salmon eggs", (120, 155), "E: receive eggs", 0),
    ("flow", "Check intake water and calibrate flow", (120, 155), "Hold E: turn flow valve", 1.5),
    ("egg_weeks", "Eggs need two farm weeks to hatch", (120, 155), "SPACE: advance two farm weeks", 0),
    ("alevins", "Nursery: inspect alevins and clear intake", (260, 174), "E: inspect / clear intake screen", 0),
    ("alevin_weeks", "Alevins need two more farm weeks", (288, 174), "SPACE: advance two farm weeks", 0),
    ("fry", "Nursery: feed and clean the growing fry", (320, 174), "SPACE: dispense starter feed", 0),
    ("fry_weeks", "Fry need three farm weeks to become smolts", (288, 174), "SPACE: advance three farm weeks", 0),
    ("screen", "Health lab: screen the ready smolts", (494, 163), "E: health screen", 0),
    ("vaccine", "Vaccinate the replacement batch", (494, 163), "Hold E: vaccinate", 2),
    ("grade", "Grader: return small fish to nursery care", (485, 268), "E: open grading flume", 0),
    ("transfer", "Transfer certified juveniles, NOT dinner", (485, 268), "E: connect transfer line", 0),
    ("exit", "Back to the pens: mature fish are ready", (320, 293), "E: leave hatchery", 0),
    ("harvest", "Load three crates of MATURE salmon", (2698, 1278), "E: prepare mature harvest", 0),
    ("drive", "Deliver mature salmon to the fish market", (3260, 1910), "E: enter truck / park / unload", 0),
    ("stamp", "Market: committee approval is required", (3260, 1910), "E: show Bernard's wet fin stamp", 0),
    ("done", "Delivery accepted. Management under review.", (3260, 1910), "ENTER: another shift", 0),
)

INTERIOR_TASKS = {task[0] for task in TASKS[6:18]}
LOADING_SPOT = (2750.0, 1285.0)
CRATE_SPOTS = ((2698, 1278), (2714, 1278), (2730, 1278))
VIDEO_DELAY = 15
VALUE_POINTS = {"feed1": 5, "feed2": 5, "feed3": 5, "nets": 10, "lice": 10,
                "eggs": 5, "flow": 5, "alevins": 5, "fry": 5, "screen": 5,
                "vaccine": 5, "grade": 5, "transfer": 10, "harvest": 5, "stamp": 15}
HQ_LINES = {"feed1": "Excellent deployment of feed capital.",
            "eggs": "Ten thousand additions to the growth pipeline.",
            "transfer": "A strong outlook for the next cohort.",
            "stamp": "We are pleased to announce that your work was our strategy."}


class HeldKeys:
    """Same indexing as pygame's key wrapper; easy to clear on pause/resume."""

    def __init__(self, held):
        self.held = held

    def __getitem__(self, key):
        return key in self.held


class SalmonShiftMixin:
    def _init_shift_ui(self):
        self.mode = "menu"
        self.menu_choice = 0
        self.shift_task = 0
        self.shift_elapsed = 0.0
        self.shift_hold = 0.0
        self.shift_bumps = 0
        self.bump_cooldown = 0.0
        self.shift_juveniles = 0
        self.shift_held_back = 0
        self.shift_screened = False
        self.shift_care = set()
        self.shift_caption = ""
        self.caption_seconds = 0.0
        self.effect = ""
        self.effect_seconds = 0.0
        self.effect_duration = 1.0
        self.shift_paused = False
        self.focused = True
        self.held_keys = set()
        self.action_release = False
        self.truck_arrival = 0.0
        self.shift_feed_point = (2506, 1255)
        self.shift_revenue = 0.0
        self.shift_driving_joke = False
        self.shift_feed_round = 0
        self.success_seconds = 0.0
        self.success_point = (0, 0)
        self.success_inside = False
        self.receipt_age = 0.0
        self.scoop_ready = False
        self.feed_aim = 0.0
        self.feed_spill = False
        self.feed_spills = 0
        self.feed_paid = False
        self.throw_point = (2476, 1287)
        self.throw_age = 10.0
        self.throw_pending = False
        self.throw_success = False
        self.throw_recovery = False
        self.throw_origin = (2476, 1287)
        self.throw_task = ""
        self.value_seconds = 0.0
        self.marketing_label = False
        self.marketing_dinged = False
        self.net_attached = False
        self.pump_connected = False
        self.pump_squeaked = False
        self.net_progress = 0.0
        self.pump_progress = 0.0
        self.flow_progress = 0.0
        self.fry_fed = False
        self.screen_started = False
        self.screen_timer = 0.0
        self.grade_open = False
        self.grade_guide = .12
        self.grade_retry = 0.0
        self.transfer_connected = False
        self.transfer_started = False
        self.transfer_progress = 0.0
        self.transfer_total = 0
        self.harvest_prepared = False
        self.carrying_crate = False
        self.loaded_crates = 0
        self.crate_bounce = 0.0
        self.market_phase = "weigh"
        self.market_timer = 0.0
        self.form_age = 0.0
        self.honk_seconds = 0.0
        self.bump_line_played = False
        self.camera_ready = False
        self.ambience_clock = 0.0
        self.album_open = False
        self.album_choice = 0
        self.album_keys = set()
        self.album_wait_release = False
        self.video_open = False
        self.video_container = None
        self.video_image = None
        self.video_error = ""
        self.video_paused = False
        # Playback survives mode resets, but never goes into a career save.
        self.audio_muted = getattr(self, "audio_muted", False)
        self._init_album()

    def _init_album(self):
        if hasattr(self, "music_tracks"):
            return
        self.music_end_event = pygame.event.custom_type()
        self.music_tracks = []
        self.music_failed = set()
        self.music_index = -1
        self.music_playing = False
        self.music_paused = False
        self.music_available = bool(pygame.mixer.get_init())
        try:
            folder = Path(__file__).resolve().parent / "Songs"
            self.music_tracks = sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"), key=lambda p: p.name.casefold())
        except OSError:
            pass
        if self.music_available:
            pygame.mixer.stop()  # Only the streamed album is audible.
        self._play_song()

    def _play_cue(self, name):
        # Keep the physical/visual gag triggers; effects are intentionally silent.
        pass

    def _play_song(self, selected=None):
        if not self.music_available:
            return
        candidates = [i for i in range(len(self.music_tracks)) if i not in self.music_failed and i != self.music_index]
        random.shuffle(candidates)
        if self.music_index >= 0 and self.music_index not in self.music_failed:
            candidates.append(self.music_index)  # Repeat only if all alternatives fail.
        if selected is not None and selected not in self.music_failed:
            candidates = [selected] + [i for i in candidates if i != selected]
        self._stop_music()
        for index in candidates:
            try:
                pygame.mixer.music.load(str(self.music_tracks[index]))
                pygame.mixer.music.set_volume(0 if self.audio_muted else .65)
                pygame.mixer.music.set_endevent(self.music_end_event)
                pygame.mixer.music.play()
            except (pygame.error, OSError):
                self.music_failed.add(index)
                continue
            self.music_index = index
            self.music_playing = True
            self._sync_music_pause()
            return

    def _stop_music(self):
        self.music_playing = False
        self.music_paused = False
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_endevent()
                pygame.mixer.music.stop()
            except pygame.error:
                self.music_available = False
        pygame.event.clear(self.music_end_event)

    def _sync_music_pause(self):
        paused = not self.focused or (self.video_open and self.video_paused) or (self.mode == "shift" and self.shift_paused and not self.album_open)
        if not self.music_playing or paused == self.music_paused:
            return
        try:
            if paused:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
            self.music_paused = paused
        except pygame.error:
            self.music_available = self.music_playing = False

    def _toggle_audio(self):
        self.audio_muted = not self.audio_muted
        if self.music_available:
            try:
                pygame.mixer.music.set_volume(0 if self.audio_muted else .65)
            except pygame.error:
                self.music_available = self.music_playing = False

    def _toggle_album(self):
        self.album_open = not self.album_open
        self.album_choice = self.music_index if self.music_playing else len(self.music_tracks) + 1
        self.held_keys.clear()
        self.shift_hold = 0
        self.action_release = False
        self.album_wait_release = True

    def _album_select(self):
        if self.album_choice == len(self.music_tracks) + 1:
            self._stop_music()
        elif self.album_choice == len(self.music_tracks):
            self._start_superstar()
        else:
            self._play_song(self.album_choice)
            if self.music_playing:
                if self.mode == "shift":
                    self.shift_paused = False
                if self.album_open:
                    self._toggle_album()

    def _album_row(self, index):
        # Five songs, the video duet, and Stop fit; longer folders scroll.
        first = max(0, min(self.album_choice - 4, len(self.music_tracks) - 5))
        return pygame.Rect(99, 115 + (index - first) * 25, 442, 22)

    def _start_superstar(self):
        self.video_error = ""
        target = next((i for i, path in enumerate(self.music_tracks)
                       if path.stem.casefold() == "whispers_of_a_dusk_breeze"), None)
        if target is None or target in self.music_failed or not self.music_available:
            self.video_error = "Whispers soundtrack unavailable. Choose another song."
            return
        try:
            import av
        except ImportError:
            self.video_error = "Video unavailable: install requirements.txt first."
            return
        self._close_video()
        try:
            path = Path(__file__).resolve().parent / "salmon_superstar_final.mp4"
            self.video_container = av.open(str(path))
            stream = self.video_container.streams.video[0]
            self.video_step = 1 / float(stream.average_rate or 30)
            # Prepare the beginning, but keep it hidden during the music intro.
            self.video_frames = self.video_container.decode(stream)
            frame = next(self.video_frames)
            if frame.time is None:
                raise ValueError("Missing video timestamp")
            self._show_video_frame(frame)
            self.video_next = next(self.video_frames, None)
            self.video_elapsed = 0.0
            self.video_paused = False
            self.video_open = True
            self.album_open = True
            self._play_song(target)  # Song begins at 0:00 after the image is ready.
            if not self.music_playing or self.music_index != target:
                raise ValueError("Soundtrack failed")
            self.held_keys.clear()
            self.shift_hold = 0
        except (av.FFmpegError, OSError, ValueError, IndexError, StopIteration):
            self._close_video()
            self.video_error = "Video unavailable. Check the MP4 and soundtrack."

    def _show_video_frame(self, frame):
        scale = min(640 / frame.width, 360 / frame.height)
        width, height = max(1, round(frame.width * scale)), max(1, round(frame.height * scale))
        rgb = frame.reformat(width=width, height=height, format="rgb24")
        plane = rgb.planes[0]
        data = bytes(plane)
        stride = width * 3
        if plane.line_size != stride:
            data = b"".join(data[y * plane.line_size:y * plane.line_size + stride] for y in range(height))
        self.video_image = pygame.image.frombytes(data, (width, height), "RGB")
        self.video_frame_time = float(frame.time)

    def _update_video(self, dt):
        if not self.video_open or self.video_paused or not self.focused:
            return
        import av
        # Follow the soundtrack clock, so opening/decoding cannot put the
        # picture ahead of the song. SDL can briefly report -1 while starting.
        latest = None
        try:
            position = pygame.mixer.music.get_pos()
            self.video_elapsed = max(self.video_elapsed, position / 1000) if position >= 0 else self.video_elapsed + dt
            target = self.video_elapsed - VIDEO_DELAY
            if target < 0:
                return
            while self.video_next is not None and float(self.video_next.time) <= target:
                latest = self.video_next
                self.video_next = next(self.video_frames, None)
            if latest is not None:
                self._show_video_frame(latest)
            if self.video_next is None and target >= self.video_frame_time + self.video_step:
                self._close_video()
        except (av.FFmpegError, pygame.error, OSError, ValueError, TypeError):
            self._close_video()
            self.video_error = "Video playback ended unexpectedly. Music can continue."

    def _close_video(self):
        self.video_open = False
        self.video_paused = False
        if self.video_container is not None:
            self.video_container.close()
            self.video_container = None
        self.video_frames = self.video_next = self.video_image = None
        self.held_keys.clear()
        self.album_wait_release = True

    def _draw_video(self):
        self.canvas.fill((7, 15, 21))
        waiting = self.video_elapsed < VIDEO_DELAY
        if waiting:
            remaining = math.ceil(VIDEO_DELAY - self.video_elapsed)
            self._draw_text(self.canvas, "WHISPERS PLAYS FIRST", (320, 164), (232, 213, 161), self.large_font, center=True)
            self._draw_text(self.canvas, f"Salmon Superstar starts in {remaining} seconds", (320, 206), center=True)
            self._draw_text(self.canvas, "The video will play from the beginning.", (320, 234), (156, 212, 194), self.small_font, center=True)
        elif self.video_image is not None:
            self.canvas.blit(self.video_image, self.video_image.get_rect(center=(320, 200)))
        stamp = int(self.video_frame_time)
        self._draw_text(self.canvas, f"SALMON SUPERSTAR  {stamp // 60}:{stamp % 60:02d} / 1:00", (10, 6), font=self.small_font)
        label = "WHISPERS OF A DUSK BREEZE"
        self._draw_text(self.canvas, label, (630 - self.small_font.size(label)[0], 6), font=self.small_font)
        self._draw_text(self.canvas, "SPACE " + ("resume" if self.video_paused else "pause") + "   V mute music   ESC / B back to album", (320, 390), font=self.small_font, center=True)

    def _album_event(self, event):
        if event.type == self.music_end_event:
            if self.music_playing:
                if self.video_open:
                    self._close_video()
                self._play_song()
            return True
        if event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED):
            self.focused = event.type == pygame.WINDOWFOCUSGAINED
            self.held_keys.clear()
            self.album_keys.clear()
            self.album_wait_release = True
            return False
        if event.type == pygame.KEYUP:
            self.album_keys.discard(event.key)
            return self.album_open
        if event.type == pygame.KEYDOWN:
            if not self.focused:
                return True
            if event.key in (pygame.K_b, pygame.K_v) or self.album_open:
                if getattr(event, "repeat", False) or event.key in self.album_keys:
                    return True
                self.album_keys.add(event.key)
                if self.video_open:
                    if event.key == pygame.K_v:
                        self._toggle_audio()
                    elif event.key in (pygame.K_b, pygame.K_ESCAPE):
                        self._close_video()
                    elif event.key == pygame.K_SPACE:
                        self.video_paused = not self.video_paused
                    return True
                if event.key == pygame.K_v:
                    self._toggle_audio()
                elif event.key == pygame.K_b or self.album_open and event.key == pygame.K_ESCAPE:
                    self._toggle_album()
                elif self.album_open:
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        self.album_choice = (self.album_choice + (1 if event.key == pygame.K_DOWN else -1)) % (len(self.music_tracks) + 2)
                    elif event.key == pygame.K_RETURN:
                        self._album_select()
                return True
        if self.album_open and event.type == pygame.MOUSEBUTTONDOWN:
            if self.video_open:
                return True
            if event.button == 1:
                ww, wh = self.window.get_size()
                scale = min(ww / 640, wh / 400)
                point = ((event.pos[0] - (ww - 640 * scale) / 2) / scale,
                         (event.pos[1] - (wh - 400 * scale) / 2) / scale)
                for i in range(len(self.music_tracks) + 2):
                    row = self._album_row(i)
                    if 115 <= row.y < 289 and row.collidepoint(point):
                        self.album_choice = i
                        self._album_select()
                        break
            return True
        return False

    def _fit_music_text(self, text, width):
        if self.small_font.size(text)[0] <= width:
            return text
        while text and self.small_font.size(text + "...")[0] > width:
            text = text[:-1]
        return text + "..."

    def _music_status(self):
        if not self.music_available or not self.music_tracks or len(self.music_failed) == len(self.music_tracks):
            return "Music unavailable"
        if not self.music_playing:
            return "Music stopped"
        name = self.music_tracks[self.music_index].stem.replace("_", " ")
        return ("Muted: " if self.audio_muted else "Now Playing: ") + name

    def _draw_album(self):
        if self.video_open:
            self._draw_video()
            return
        veil = pygame.Surface((640, 400), pygame.SRCALPHA)
        veil.fill((10, 27, 34, 220))
        self.canvas.blit(veil, (0, 0))
        pygame.draw.rect(self.canvas, (24, 49, 54), (82, 45, 476, 308))
        pygame.draw.rect(self.canvas, (238, 206, 129), (82, 45, 476, 308), 2)
        self._draw_text(self.canvas, "THE SALMON ALBUM", (320, 70), (246, 226, 179), self.large_font, center=True)
        self._draw_text(self.canvas, self._fit_music_text(self._music_status(), 434), (102, 94), (156, 212, 194), self.small_font)
        for i in range(len(self.music_tracks) + 2):
            row = self._album_row(i)
            if not 115 <= row.y < 289:
                continue
            chosen = i == self.album_choice
            pygame.draw.rect(self.canvas, (60, 107, 102) if chosen else (33, 66, 69), row)
            if chosen:
                pygame.draw.rect(self.canvas, (245, 214, 134), row, 1)
            playing = self.music_playing and i == self.music_index
            name = (self.music_tracks[i].stem.replace("_", " ") if i < len(self.music_tracks)
                    else f"VIDEO: Superstar + Whispers ({VIDEO_DELAY}s delay)" if i == len(self.music_tracks)
                    else "Stop Music")
            label = ("> " if playing else "  ") + name + (" [unavailable]" if i in self.music_failed else "")
            self._draw_text(self.canvas, self._fit_music_text(label, 423), (row.x + 8, row.y + 8), (245, 232, 191), self.small_font)
        self._draw_text(self.canvas, self._fit_music_text(self.video_error or "Choose a song, or watch the video with Whispers.", 438), (320, 304), (175, 211, 201), self.small_font, center=True)
        self._draw_text(self.canvas, "Pick a song to return to play with music.", (320, 322), font=self.small_font, center=True)
        self._draw_text(self.canvas, "B / ESC close     V " + ("unmute" if self.audio_muted else "mute") + " music", (320, 339), font=self.small_font, center=True)

    def _art_time(self):
        return self.shift_elapsed if self.mode == "shift" else pygame.time.get_ticks() / 1000

    def _bernard_expression(self):
        if self.shift_juveniles or self._task()[0] in ("stamp", "done"):
            return "impressed"
        return "outraged" if self.shift_task in (1, 2) else "suspicious"

    def _draw_fish(self, target, x, y, length=14, phase=0, facing=1,
                   bernard=False, expression="suspicious", clipboard=False):
        """One pixel silhouette reused for the school, Bernard and his portrait."""
        fish = pygame.Surface((32, 21), pygame.SRCALPHA)
        tail = 2 if math.sin(phase * 7) > 0 else -1
        pygame.draw.polygon(fish, (87, 125, 128), [(9, 9), (1, 4 + tail), (2, 14 + tail)])
        pygame.draw.ellipse(fish, (191, 213, 202), (7, 3, 24, 12))
        pygame.draw.line(fish, (61, 103, 112), (13, 4), (25, 4), 2)
        pygame.draw.line(fish, (225, 144, 137), (10, 10), (28, 10), 3)
        pygame.draw.line(fish, (244, 225, 185), (13, 13), (25, 13))
        pygame.draw.polygon(fish, (85, 134, 135), [(15, 5), (18, 0), (23, 5)])
        pygame.draw.polygon(fish, (108, 142, 138), [(18, 11), (15, 17), (23, 12)])
        pygame.draw.rect(fish, (28, 53, 61), (26, 6, 2, 2))
        if bernard:
            pygame.draw.rect(fish, (255, 215, 78), (15, 6, 5, 5))
            if expression == "outraged":
                pygame.draw.line(fish, (37, 57, 60), (23, 3), (29, 5), 2)
                pygame.draw.rect(fish, (37, 57, 60), (28, 10, 2, 3))
            elif expression == "impressed":
                pygame.draw.line(fish, (37, 57, 60), (24, 2), (29, 2))
                pygame.draw.line(fish, (37, 57, 60), (26, 11), (29, 10))
            else:
                pygame.draw.line(fish, (37, 57, 60), (23, 4), (29, 3), 2)
            if clipboard:
                pygame.draw.rect(fish, (115, 76, 49), (3, 10, 11, 11))
                pygame.draw.rect(fish, (239, 222, 173), (4, 11, 9, 9))
                pygame.draw.rect(fish, (121, 145, 139), (7, 10, 4, 2))
                pygame.draw.line(fish, (123, 143, 126), (6, 15), (11, 15))
                pygame.draw.line(fish, (123, 143, 126), (6, 18), (10, 18))
        if facing < 0:
            fish = pygame.transform.flip(fish, True, False)
        height = max(7, round(length * 21 / 32))
        fish = pygame.transform.scale(fish, (length, height))
        target.blit(fish, (round(x - length / 2), round(y - height / 2)))

    def _draw_portrait(self, speaker, x, y):
        pygame.draw.rect(self.canvas, (45, 83, 80), (x, y, 52, 39), border_radius=3)
        if speaker == "HEAD OFFICE":
            pygame.draw.rect(self.canvas, (27, 47, 73), (x + 3, y + 3, 46, 33))
            pygame.draw.arc(self.canvas, (230, 206, 131), (x + 7, y + 5, 23, 19), 0, math.pi, 4)
            pygame.draw.rect(self.canvas, (230, 206, 131), (x + 6, y + 12, 7, 8))
            pygame.draw.rect(self.canvas, (230, 206, 131), (x + 25, y + 12, 7, 8))
            pygame.draw.lines(self.canvas, (126, 204, 174), False, [(x + 11, y + 30), (x + 21, y + 25), (x + 30, y + 28), (x + 42, y + 14)], 2)
        elif speaker == "BERNARD":
            self._draw_fish(self.canvas, x + 25, y + 17, 47, self._art_time(), bernard=True,
                            expression=self._bernard_expression(), clipboard=True)
            if self.hatchery["vaccinated"]:
                pygame.draw.circle(self.canvas, (245, 210, 102), (x + 35, y + 25), 2)
            if self.in_truck:
                self._draw_text(self.canvas, "FARM COMMITTEE", (x + 57, y + 35), (171, 205, 180), self.small_font)
        else:
            clerk = speaker == "CLERK"
            pygame.draw.rect(self.canvas, (200, 161, 116), (x + 17, y + 6, 19, 20))
            pygame.draw.rect(self.canvas, (240, 196, 150), (x + 18, y + 8, 17, 15))
            pygame.draw.rect(self.canvas, (83, 111, 109) if clerk else (222, 169, 72), (x + 13, y + 25, 28, 10))
            pygame.draw.rect(self.canvas, (59, 75, 76) if clerk else (179, 80, 60), (x + 15, y + 3, 24, 7))
            pygame.draw.rect(self.canvas, (40, 61, 65), (x + 21, y + 12, 2, 2))
            pygame.draw.rect(self.canvas, (40, 61, 65), (x + 30, y + 12, 2, 2))
            pygame.draw.line(self.canvas, (125, 84, 72), (x + 24, y + 20), (x + 30, y + 20))
            if clerk:
                pygame.draw.rect(self.canvas, (233, 221, 177), (x + 28, y + 25, 13, 9))
        self._draw_text(self.canvas, speaker, (x + 26, y + 44), (177, 211, 191), self.small_font, center=True)

    def _start_mode(self, mode):
        # Reset runtime state in one place; construction does not load a save.
        self._close_video()
        self.__init__(save_path=self.save_path, legacy_path=self.legacy_path)
        self.mode = mode
        if mode == "career":
            self._load_saved_or_legacy()
        elif mode == "shift":
            self.fish = 1000  # Mature stock only; Bernard is one of the 666 left.
            self.average_weight = 3.6
            self.feed = 3000.0
            self.water = 72
            self.oxygen = 84
            self.lice = 36
            self.health = 85
            self.day_clock = 12.0
            self.player_x, self.player_y = 2476.0, 1300.0
            self.truck_x, self.truck_y = LOADING_SPOT
            self.truck_heading = 2.0
            self.contract = {"company": "Salmon Committee", "target": 1200.0,
                             "delivered": 0.0, "reward": 0}
            self._say("MARA: One delivery before lunch. Head Office calls it shareholder value.", "welcome", 9)

    def _say(self, caption, effect="", seconds=6):
        self.panel_message = ""
        self.shift_caption = caption
        self.caption_seconds = seconds
        if effect:
            self.effect = effect
            self.effect_seconds = seconds
            self.effect_duration = seconds

    def _shareholder_value(self):
        # Progress is the source of truth: inputs and cosmetic labels cannot add points.
        return sum(VALUE_POINTS.get(task[0], 0) for task in TASKS[:self.shift_task])

    def _head_office(self, task):
        # Four authored completion beats, using the existing caption only.
        self._say("HEAD OFFICE: " + HQ_LINES[task], seconds=6)

    def _feed_preview(self):
        # Centre each generous throw on an actual lower pen, including the
        # left/right deck positions. The same landing is used for the flight.
        pen_x = 2524 if self._task()[0] == "feed1" else 2628
        landing = (pen_x + math.sin(self.feed_aim) * 35, 1228 + (1 - math.cos(self.feed_aim)) * 70)
        return landing, abs(self.feed_aim) <= .85

    def _begin_feed_throw(self, recovery=False):
        self.throw_task = self._task()[0]
        self.throw_origin = self._task_target()
        self.throw_point, self.throw_success = self._feed_preview()
        self.throw_recovery = recovery
        if recovery:
            self.throw_point = (2524 if self.throw_task == "feed1" else 2628, 1230)
            self.throw_success = True
        else:
            self.feed -= 250
            self.feed_paid = True
        self.scoop_ready = False
        self.throw_age = 0.0
        self.throw_pending = True
        self._play_cue("water" if recovery else "scatter")

    def _land_feed(self):
        if not self.throw_pending:
            return
        self.throw_pending = False
        if self.throw_success:
            self._play_cue("splash")
            self._shift_complete(self.throw_task)
            if self.throw_recovery and self.throw_task != "feed1":
                self._say("MARA: Good recovery. They'll eat that.", "feed", 6)
        else:
            self.feed_spill = True
            self.feed_spills += 1
            self._say("BERNARD: WASTE REDUCTION. The chute is ready for your recovery.", "spill", 6)

    def _task(self):
        return TASKS[self.shift_task]

    def _task_target(self):
        if self._task()[0] == "harvest" and self.harvest_prepared:
            return LOADING_SPOT if self.carrying_crate else CRATE_SPOTS[min(2, self.loaded_crates)]
        if self._task()[0] == "drive" and not self.in_truck:
            return self.truck_x, self.truck_y
        return self._task()[2]

    def _task_near(self):
        task = self._task()[0]
        if (task in INTERIOR_TASKS) != self.inside_hatchery:
            return False
        position = ((self.interior_x, self.interior_y) if self.inside_hatchery else
                    (self.truck_x, self.truck_y) if self.in_truck else (self.player_x, self.player_y))
        radius = 82 if self.in_truck else 48 if self.carrying_crate else 85 if task == "nets" and self.net_attached else 32
        return math.dist(position, self._task_target()) < radius

    def _shift_complete(self, expected):
        """Apply one task once, only at its location and in the correct order."""
        task = self._task()[0]
        landed = task.startswith("feed") and self.throw_task == task and self.throw_success and self.throw_age >= .45 and not self.throw_pending
        automatic = landed or task == "screen" and self.screen_started or task == "transfer" and self.transfer_started or task == "harvest" and self.loaded_crates == 3
        if task != expected or task == "done" or not (self._task_near() or automatic):
            return False
        completed_point, completed_inside = self._task_target(), self.inside_hatchery
        batch = self.hatchery
        if task.startswith("feed"):
            if not (self.feed_paid and landed):
                return False
            self.shift_feed_point = self.throw_point
            self.shift_feed_round = int(task[-1])
            self.effect, self.effect_seconds, self.effect_duration = "feed", 7, 7
            if task == "feed3":
                self._say("BERNARD: Official quality control.", "feed", 7)
                self.health = min(100, self.health + 5)
                self.shift_care.add("Fed")
            self.scoop_ready = self.feed_paid = self.feed_spill = False
        elif task == "nets":
            if self.net_progress < 3:
                return False
            self.water = min(100, self.water + 18)
            self.shift_care.add("Cleaned")
            self._say("MARA: Better flow. Happier fish. Longer paperwork.", "paper", 7)
            self.player_x += 6
            self.net_attached = False
        elif task == "lice":
            if self.pump_progress < 2:
                return False
            self.lice = max(0, self.lice - 28)
            self.health = min(100, self.health + 3)
            self.shift_care.add("Treated")
            self._say("MARA: The tenants dispute the decision.", "lice", 7)
        elif task == "enter":
            self.hatchery_exit_x, self.hatchery_exit_y = self.player_x, self.player_y
            self.inside_hatchery = True
            self.interior_x, self.interior_y = 320.0, 293.0
        elif task == "eggs":
            batch.update(stage="eggs", count=10000, quality=85, weeks=0)
            self.effect, self.effect_seconds, self.effect_duration = "eggs", 7, 7
        elif task == "flow":
            if self.flow_progress < 1.5:
                return False
            batch["quality"] = min(100, (self.water + self.oxygen) // 2 + 8)
            self.effect, self.effect_seconds, self.effect_duration = "flow", 5, 5
        elif task.endswith("_weeks"):
            required_stage = {"egg_weeks": "eggs", "alevin_weeks": "alevins", "fry_weeks": "fry"}[task]
            if batch["stage"] != required_stage:
                return False
            weeks = 3 if task == "fry_weeks" else 2
            for _ in range(weeks):
                batch["count"] = int(batch["count"] * .995)
                if batch["stage"] != "eggs":
                    batch["feed_kg"] -= 250
            self.week += weeks
            batch["stage"] = {"egg_weeks": "alevins", "alevin_weeks": "fry", "fry_weeks": "smolt_ready"}[task]
            batch["weeks"] = 0
            word = "Three" if weeks == 3 else "Two"
            caption = "Your probation continues." if task == "egg_weeks" else "The replacement batch is growing."
            self._say(f"{word} farm weeks later. {caption}", "calendar", 2.5)
        elif task in ("alevins", "fry"):
            if batch["stage"] != task or batch["feed_kg"] < 250:
                return False
            if task == "fry" and not self.fry_fed:
                return False
            batch["feed_kg"] -= 250
            batch["quality"] = min(100, batch["quality"] + 5)
            caption = ("MARA: Their first workplace improvement. That's the next cohort looked after."
                       if task == "alevins" else "MARA: This meeting has excellent attendance.")
            self._say(caption, "nursery", 5)
        elif task == "screen":
            if batch["stage"] != "smolt_ready" or not self.screen_started or self.screen_timer > 0:
                return False
            self.shift_screened = True
            batch["quality"] = min(100, batch["quality"] + 3)
            self._say("HEALTH SCREEN: clear. Ready for vaccination.", "screen", 4)
        elif task == "vaccine":
            if not self.shift_screened or batch["stage"] != "smolt_ready":
                return False
            batch["vaccinated"] = True
            self._say("BERNARD: Mine is supervisory.", "vaccine", 6)
        elif task == "grade":
            if not batch["vaccinated"] or batch["stage"] != "smolt_ready" or not self.grade_open or not .25 <= self.grade_guide <= .75:
                return False
            self.shift_held_back = int(batch["count"] * .03)
            batch["count"] -= self.shift_held_back
            batch["graded"] = True
            self.grade_open = False
            self._say("MARA: Promotion postponed.", "grade", 3)
        elif task == "transfer":
            if not (self.shift_screened and batch["vaccinated"] and batch["graded"] and batch["stage"] == "smolt_ready" and self.transfer_progress >= 1):
                return False
            self.shift_juveniles = self.transfer_total
            batch["transferred_total"] = self.shift_juveniles
            batch.update(stage="empty", count=0)
            self.truck_arrival = 3.0
            self.effect, self.effect_seconds, self.effect_duration = "transfer", 8, 8
        elif task == "exit":
            self.inside_hatchery = False
            self.player_x, self.player_y = self.hatchery_exit_x, self.hatchery_exit_y
            self.truck_arrival = 3.0
        elif task == "harvest":
            if not self.harvest_prepared or self.loaded_crates != 3 or not self.shift_juveniles:
                return False
            self._say("MARA: Good. Mature fish to market. Little ones stay home.", "crates", 7)
        elif task == "drive":
            if not self.in_truck or abs(self.truck_speed) > 14 or self.truck_cargo_kg <= 0:
                return False
            self.truck_speed = 0
            self.market_phase, self.market_timer = "weigh", 1.8
            self._say("CLERK: Lovely salmon. Do you have committee approval?", "manifest", 8)
        elif task == "stamp":
            if self.truck_cargo_kg <= 0 or self.market_phase != "approve":
                return False
            self.shift_revenue = round(self.truck_cargo_kg * 8.4, 2)
            self.contract["delivered"] = self.truck_cargo_kg
            self.harvested_kg = self.truck_cargo_kg
            self.truck_cargo_kg = 0
            self.total_sales = int(self.shift_revenue)
            self.effect, self.effect_seconds, self.effect_duration = "stamp", 3, 3
            self.receipt_age = 0.0
        cue = ("plop" if task.startswith("feed") or task == "eggs" else
               "paper" if task in ("nets", "drive") else
               "pump" if task in ("flow", "alevins", "fry", "grade") else
               "splash" if task in ("lice", "transfer") else
               "plop" if task == "vaccine" else None)
        if cue:
            self._play_cue(cue)
        self.success_point = completed_point
        self.success_inside = completed_inside
        self.success_seconds = 1.0
        self.shift_task += 1
        if task in VALUE_POINTS:
            self.value_seconds = 1.4
            self._play_cue("corporate")
        if task in HQ_LINES:
            self._head_office(task)
        self.shift_hold = 0
        self.action_release = bool(self.held_keys & {pygame.K_e, pygame.K_SPACE})
        return True

    def _shift_help(self):
        if self._task()[0] in ("done", "stamp"):
            return
        if self.in_truck:
            self.truck_x, self.truck_y = LOADING_SPOT
            self.truck_heading = 2.0
        elif self.inside_hatchery:
            self.interior_x, self.interior_y = self._task_target()
        else:
            self.player_x, self.player_y = self._task_target()
            # The truck's centre is not a safe pedestrian exit/approach.
            if self._task()[0] == "drive" or self.carrying_crate:
                self.player_x += 32
        self.truck_speed = 0
        self.shift_hold = 0
        self.held_keys.clear()
        self.action_release = True

    def _shift_key(self, key):
        task = self._task()[0]
        if key == pygame.K_h:
            self._shift_help()
            return
        if key in (pygame.K_F5, pygame.K_F9):
            # A small inline notice; never call either career I/O method.
            self.panel_message = "Short shifts are served fresh. Career saves are safe."
            return
        if self.action_release or (self.effect_seconds > 0 and self.effect in ("calendar", "grade")):
            return
        if task == "drive" and self.in_truck and key == pygame.K_SPACE:
            self.honk_seconds = 1.5
            self._play_cue("horn")
            return
        if self.carrying_crate and key == pygame.K_SPACE:
            self.marketing_label = not self.marketing_label
            if not self.marketing_dinged:
                self.marketing_dinged = True
                self._play_cue("corporate")
                self._say("MARA: Still fish.", seconds=3)
            return
        if task == "drive" and key == pygame.K_e:
            if self.in_truck:
                if self._task_near():
                    self._shift_complete("drive")
                elif abs(self.truck_speed) < 14:
                    for dx, dy in ((32, 0), (-32, 0), (0, 32), (0, -32), (48, 48)):
                        if self._walkable(self.truck_x + dx, self.truck_y + dy):
                            self.player_x, self.player_y = self.truck_x + dx, self.truck_y + dy
                            self.in_truck = False
                            break
            elif math.dist((self.player_x, self.player_y), (self.truck_x, self.truck_y)) < 65:
                self.in_truck = True
                self.truck_speed = 0
            return
        if not self._task_near():
            if self.inside_hatchery and key == pygame.K_e:
                self.panel_message = "MARA: Follow the gold arrow to the active station."
            return
        if task.startswith("feed"):
            if self.throw_pending:
                return
            if self.feed_spill and key == pygame.K_e:
                self._begin_feed_throw(recovery=True)
            elif key == pygame.K_e:
                self.scoop_ready = not self.scoop_ready
                self.feed_aim = 0
            elif key == pygame.K_SPACE and self.scoop_ready and not self.feed_spill:
                self._begin_feed_throw()
            return
        if task == "nets":
            if key == pygame.K_e:
                if not self.net_attached:
                    self._play_cue("creak")
                self.net_attached = True
            return
        if task == "lice":
            if key == pygame.K_e:
                self.pump_connected = True
                self._play_cue("pump")
            return
        if task == "fry":
            if key == pygame.K_SPACE and not self.fry_fed:
                self.fry_fed = True
                self._say("MARA: Starter feed served. Now clear the outlet with E.", "nursery", 4)
                self._play_cue("plop")
            elif key == pygame.K_e and self.fry_fed:
                self._shift_complete(task)
            return
        if task == "screen":
            if key == pygame.K_e and not self.screen_started:
                self.screen_started, self.screen_timer = True, 1.5
                self._play_cue("pump")
            return
        if task == "grade":
            if key == pygame.K_e:
                self.grade_open = not self.grade_open
            elif key == pygame.K_SPACE and self.grade_open:
                if not self._shift_complete(task):
                    self.grade_retry = 2.0
                    self._say("MARA: Aim the guide into the broad green band. They'll loop safely around.", seconds=5)
                    self._play_cue("water")
            return
        if task == "transfer":
            if key == pygame.K_e:
                self.transfer_connected = True
            elif key == pygame.K_SPACE and self.transfer_connected and not self.transfer_started:
                if not (self.shift_screened and self.hatchery["vaccinated"] and self.hatchery["graded"]):
                    self.panel_message = "MARA: Screen, vaccinate and grade this batch before transfer."
                    return
                self.transfer_started = True
                self.transfer_total = self.hatchery["count"]
                self._play_cue("water")
            return
        if task == "harvest" and key == pygame.K_e:
            if not self.harvest_prepared:
                if self.fish < 334 or not self.shift_juveniles:
                    return
                self.harvest_prepared = True
                self.fish -= 334
                self._say("MARA: Three crates of mature salmon. E to carry, E by the truck to load.", "crates", 7)
            elif not self.carrying_crate:
                self.carrying_crate = True
            else:
                self.carrying_crate = False
                self.loaded_crates += 1
                self.truck_cargo_kg = round(400.8 * self.loaded_crates, 1)
                self.crate_bounce = .6
                self.value_seconds = 1.4
                self._play_cue("crate")
                if self.loaded_crates == 3:
                    self._shift_complete(task)
            return
        if task == "stamp":
            if key == pygame.K_SPACE and self.market_phase == "signature":
                self.market_phase = "approve"
                self.form_age = 0
                self._say("CLERK: Finally. The short form.", seconds=5)
                self._play_cue("paper")
            elif key == pygame.K_e and self.market_phase == "approve":
                self._shift_complete(task)
            return
        if self._task()[4]:
            return
        wanted = pygame.K_SPACE if task.startswith("feed") or task.endswith("_weeks") else pygame.K_e
        if key == wanted:
            self._shift_complete(task)

    def _shift_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self.held_keys.clear()
            if self.mode == "shift":
                self.shift_paused = True
                self.shift_hold = 0
                if pygame.mixer.get_init():
                    pygame.mixer.stop()
            return
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
            return
        if event.type == pygame.KEYUP:
            self.held_keys.discard(event.key)
            if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_h):
                self.action_release = False
                if self._task()[0] not in ("nets", "lice", "flow"):
                    self.shift_hold = 0
            return
        if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
            return
        key = event.key
        if key in self.held_keys:
            return
        self.held_keys.add(key)
        if key == pygame.K_v:
            self._toggle_audio()
            return
        if self.mode == "menu":
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_choice = (self.menu_choice - 1) % 3
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_choice = (self.menu_choice + 1) % 3
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.menu_choice == 2:
                    self.running = False
                else:
                    self._start_mode("shift" if self.menu_choice == 0 else "career")
            return
        if self._task()[0] == "done":
            if key == pygame.K_RETURN:
                self._start_mode("shift")
            elif key in (pygame.K_ESCAPE, pygame.K_m):
                self._start_mode("menu")
            return
        if key == pygame.K_ESCAPE:
            if self.focused:
                self.shift_paused = not self.shift_paused
            self.held_keys.clear()
            self.shift_hold = 0
            self.action_release = False
            if self.shift_paused and pygame.mixer.get_init():
                pygame.mixer.stop()
            return
        if self.shift_paused:
            if key == pygame.K_RETURN and self.focused:
                self.shift_paused = False
                self.held_keys.clear()
                self.action_release = False
            elif key == pygame.K_m:
                self._start_mode("menu")
            return
        if self.focused:
            self._shift_key(key)

    def _update_shift(self, dt):
        if self.mode != "shift" or self.shift_paused or not self.focused:
            return
        # Count actual active time, but keep movement stable during frame stalls.
        if self._task()[0] != "done":
            self.shift_elapsed += dt
        dt = min(dt, .05)
        self.caption_seconds = max(0, self.caption_seconds - dt)
        self.value_seconds = max(0, self.value_seconds - dt)
        self.effect_seconds = max(0, self.effect_seconds - dt)
        self.bump_cooldown = max(0, self.bump_cooldown - dt)
        self.truck_arrival = max(0, self.truck_arrival - dt)
        self.success_seconds = max(0, self.success_seconds - dt)
        self.throw_age += dt
        if self.throw_pending and self.throw_age >= .45:
            self._land_feed()
        self.grade_retry = max(0, self.grade_retry - dt)
        self.crate_bounce = max(0, self.crate_bounce - dt)
        self.honk_seconds = max(0, self.honk_seconds - dt)
        self.ambience_clock -= dt
        if self.ambience_clock <= 0:
            self._play_cue("indoor" if self.inside_hatchery else "outdoor")
            self.ambience_clock = 1.1
        if self._task()[0] == "done":
            previous_age = self.receipt_age
            self.receipt_age += dt
            if previous_age < .35 <= self.receipt_age:
                self._play_cue("stamp")
        if self._task()[0] == "stamp":
            self.form_age += dt
            if self.market_phase == "weigh":
                self.market_timer = max(0, self.market_timer - dt)
                if self.market_timer <= 0:
                    self.market_phase = "signature"
                    self._play_cue("reject")
                    self._say("CLERK: Fish accepted. Human signature rejected. Committee authorization?", "manifest", 7)
            return
        if self._task()[0] == "done":
            return
        if self._task()[0] == "screen" and self.screen_started:
            self.screen_timer = max(0, self.screen_timer - dt)
            if self.screen_timer == 0:
                self._shift_complete("screen")
        if self._task()[0] == "transfer" and self.transfer_started:
            self.transfer_progress = min(1.0, self.transfer_progress + dt / 2.2)
            self.shift_juveniles = int(self.transfer_total * self.transfer_progress)
            self.hatchery["count"] = self.transfer_total - self.shift_juveniles
            if self.transfer_progress >= 1:
                self._shift_complete("transfer")
        locked = self.effect_seconds > 0 and self.effect in ("calendar", "grade")
        keys = HeldKeys(self.held_keys)
        task = self._task()[0]
        horizontal = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
        aiming = task.startswith("feed") and self.scoop_ready
        guiding = task == "grade" and self.grade_open
        pulling = task == "nets" and self.net_attached and self._task_near() and keys[pygame.K_e] and horizontal > 0
        operating = task == "lice" and self.pump_connected and self._task_near() and keys[pygame.K_SPACE]
        turning = task == "flow" and self._task_near() and keys[pygame.K_e]
        if aiming:
            self.feed_aim = max(-1.8, min(1.8, self.feed_aim + horizontal * dt * 1.2))
        if guiding:
            self.grade_guide = max(0, min(1, self.grade_guide + horizontal * dt * .6))
        if pulling and not self.action_release:
            if int(self.net_progress) != int(min(3, self.net_progress + dt)):
                self._play_cue("creak")
            self.net_progress = min(3, self.net_progress + dt)
            if self._walkable(self.player_x + 14 * dt, self.player_y):
                self.player_x += 14 * dt
            self.shift_hold = self.net_progress
            if self.net_progress >= 3:
                self._shift_complete("nets")
        elif operating and not self.action_release:
            if int(self.pump_progress * 4) != int(min(2, self.pump_progress + dt) * 4):
                self._play_cue("pump")
            self.pump_progress = min(2, self.pump_progress + dt)
            self.shift_hold = self.pump_progress
            if self.pump_progress >= 2:
                self._shift_complete("lice")
        elif turning and not self.action_release:
            self.flow_progress = min(1.5, self.flow_progress + dt)
            self.shift_hold = self.flow_progress
            if self.flow_progress >= 1.5:
                self._shift_complete("flow")
        if not locked:
            if self.in_truck:
                bumps = self.shift_bumps
                self._move_truck(dt, keys)
                if self.shift_bumps > bumps and not self.bump_line_played:
                    self.bump_line_played = True
                    self._say("MARA: ... Still salmon.", "bump", 4)
                    self._play_cue("crate")
                loading_read = self.effect != "crates" or self.effect_duration - self.effect_seconds >= 4
                at_bend = math.dist((self.truck_x, self.truck_y), LOADING_SPOT) > 90
                bump_read = self.effect != "bump" or self.caption_seconds <= 0
                if self.truck_speed > 12 and not self.shift_driving_joke and loading_read and bump_read and at_bend:
                    self.shift_driving_joke = True
                    self._say("MARA: Brake gently. That is dinner. It has standards.", "driving", 8)
            elif not (aiming or guiding or pulling or operating or turning):
                self._move_player(dt, keys)
        if self.effect == "lice" and self.effect_duration - self.effect_seconds > 1 and keys[pygame.K_SPACE] and not self.pump_squeaked:
            self.pump_squeaked = True
            self._say("BERNARD: THEY HAVE LEFT.", "lice", 4)
            self._play_cue("squeak")
        # Only vaccination uses a reset-on-release hold. Physical tools retain work.
        if self._task()[0] == "vaccine" and self._task_near() and keys[pygame.K_e] and not self.action_release and not locked:
            self.shift_hold += dt
            if self.shift_hold + 1e-6 >= self._task()[4]:
                self._shift_complete(self._task()[0])
        elif self._task()[0] not in ("nets", "lice", "flow"):
            self.shift_hold = 0

    def _shift_lines(self, text, x, y, width, color=(246, 239, 210), font=None, line_height=15):
        font = font or self.font
        line = ""
        for word in text.split():
            candidate = (line + " " + word).strip()
            if line and font.size(candidate)[0] > width:
                self._draw_text(self.canvas, line, (x, y), color, font)
                y += line_height
                line = word
            else:
                line = candidate
        self._draw_text(self.canvas, line, (x, y), color, font)
        return y + line_height

    def _draw_shift_title(self):
        t = self._art_time()
        self.canvas.fill((24, 57, 65))
        self._draw_text(self.canvas, "TIDE & TACKLE", (320, 28), font=self.large_font, center=True)
        self._draw_text(self.canvas, "A short shift. An extraordinary commitment to shareholder value.", (320, 55), (232, 180, 134), self.small_font, center=True)
        pygame.draw.rect(self.canvas, (104, 151, 148), (68, 79, 504, 118))
        pygame.draw.polygon(self.canvas, (80, 121, 124), [(68, 112), (125, 83), (179, 115), (230, 94), (293, 127), (68, 127)])
        pygame.draw.polygon(self.canvas, (63, 105, 114), [(353, 122), (420, 87), (480, 115), (525, 91), (572, 110), (572, 137)])
        pygame.draw.rect(self.canvas, (47, 119, 137), (68, 124, 504, 73))
        for i in range(22):
            rx = 75 + (i * 73) % 477
            ry = 130 + (i * 13) % 64
            pygame.draw.line(self.canvas, (74, 146, 155), (rx, ry), (rx + 9 + int(math.sin(t + i) * 3), ry))
        pygame.draw.rect(self.canvas, (165, 123, 80), (72, 171, 496, 19))
        for px in range(76, 568, 13):
            pygame.draw.line(self.canvas, (206, 164, 110), (px, 172), (px, 189))
        pygame.draw.ellipse(self.canvas, (25, 83, 105), (125, 133, 141, 39))
        pygame.draw.ellipse(self.canvas, (232, 202, 136), (122, 130, 147, 42), 3)
        for i in range(5):
            self._draw_fish(self.canvas, 153 + i * 21 + math.sin(t + i) * 4, 151 + math.sin(t * 2 + i) * 4, 19, t + i)
        self._draw_fish(self.canvas, 427, 142 + math.sin(t * 2) * 3, 92, t,
                        bernard=True, expression="suspicious", clipboard=True)
        self._draw_text(self.canvas, self._fit_music_text(self._music_status(), 504), (320, 205), (178, 212, 189), self.small_font, center=True)
        for i, label in enumerate(("FIVE-MINUTE SALMON SHIFT", "FARM CAREER", "QUIT")):
            rect = pygame.Rect(134, 225 + i * 37, 372, 30)
            pygame.draw.rect(self.canvas, (70, 126, 111) if i == self.menu_choice else (34, 74, 76), rect)
            if i == self.menu_choice:
                pygame.draw.rect(self.canvas, (243, 208, 124), rect, 2)
                self._draw_text(self.canvas, ">", (145, rect.y + 9), (255, 221, 124))
            self._draw_text(self.canvas, label, rect.center, center=True)
        self._draw_text(self.canvas, "UP/DOWN choose  ENTER start  B Album  V music " + ("OFF" if self.audio_muted else "ON"), (320, 351), center=True)
        self._draw_text(self.canvas, "A short shift. No saving required. Your career stays separate.", (320, 378), (178, 212, 189), self.small_font, center=True)

    def _chapter(self):
        if self.shift_task < 5:
            return "1 / 5  CARE"
        if self.shift_task < 13:
            return "2 / 5  HATCHERY"
        if self.shift_task < 18:
            return "3 / 5  CERTIFICATION"
        return "4 / 5  DELIVERY" if self.shift_task < 20 else "5 / 5  MARKET"

    def _interaction_prompt(self):
        task = self._task()[0]
        if task.startswith("feed"):
            if self.throw_pending:
                return "Pellets on their way... (you can move)"
            if self.feed_spill:
                return "E: sweep spill into recovery chute (no extra feed)"
            return "A / D aim   SPACE throw   E put scoop down" if self.scoop_ready else "E: take scoop"
        if task == "nets":
            return "Hold E + D / RIGHT: pull back (progress stays)" if self.net_attached else "E: grip maintenance pole"
        if task == "lice":
            return "Hold SPACE: operate treatment pump" if self.pump_connected else "E: connect treatment hose"
        if task == "fry":
            return "E: clean tank outlet" if self.fry_fed else "SPACE: dispense starter feed"
        if task == "screen" and self.screen_started:
            return "Screening WATER / CONDITION / READINESS..."
        if task == "grade" and self.grade_open:
            return "A / D guide into GREEN   SPACE confirm   E close"
        if task == "transfer":
            return "Transfer flowing... juveniles stay at the farm" if self.transfer_started else "SPACE: open transfer flow" if self.transfer_connected else "E: connect transfer line"
        if task == "harvest" and self.harvest_prepared:
            return f"E: Load crate {self.loaded_crates + 1}/3   SPACE: flip label" if self.carrying_crate else f"E: carry crate {self.loaded_crates + 1}/3"
        if task == "drive":
            return "W / S drive / brake   A / D steer   SPACE horn   E park" if self.in_truck else "E: enter the farm truck"
        if task == "stamp":
            return "Weighing delivery..." if self.market_phase == "weigh" else "SPACE: unfold committee authorization" if self.market_phase == "signature" else "E: place Bernard's wet finprint"
        return self._task()[3]

    def _draw_shift_frame(self):
        if self.mode == "menu":
            self._draw_shift_title()
            return

        if not self.inside_hatchery:
            x, y = (self.truck_x, self.truck_y) if self.in_truck else (self.player_x, self.player_y)
            if not self.in_truck and math.dist((x, y), (2576, 1192)) < 225:
                desired_x, desired_y = 2256, 990
            else:
                desired_x, desired_y = x - 320, y - 235
            desired_x = max(0, min(self.world_width - 640, desired_x))
            desired_y = max(0, min(self.world_height - 336, desired_y))
            ease = .16 if self.camera_ready else 1
            self.camera_x += (desired_x - self.camera_x) * ease
            self.camera_y += (desired_y - self.camera_y) * ease
            self.camera_ready = True
        self._draw_world()
        self._draw_shift_props()
        self._draw_shift_target()

        pygame.draw.rect(self.canvas, (24, 49, 49), (8, 6, 530, 72))
        pygame.draw.rect(self.canvas, (112, 203, 173), (8, 6, 530, 72), 1)
        task = self._task()
        self._draw_text(self.canvas, self._chapter(), (16, 12), (154, 206, 181), self.small_font)
        self._draw_text(self.canvas, self._fit_music_text(self._music_status(), 376), (155, 12), (154, 206, 181), self.small_font)
        self._draw_text(self.canvas, task[1], (16, 27))
        prompt = self._interaction_prompt()
        self._draw_text(self.canvas, prompt, (16, 44), (255, 222, 136))
        if self.inside_hatchery:
            stage = str(self.hatchery["stage"]).replace("_", " ").upper()
            detail = (f"INTAKE: WATER {self.water}% / OXYGEN {self.oxygen}%" if task[0] in ("flow", "egg_weeks") else
                      f"{stage}  {self.hatchery['count']:,} fish  QUALITY {self.hatchery['quality']}%  FEED {self.hatchery['feed_kg']} kg")
        else:
            position = (self.truck_x, self.truck_y) if self.in_truck else (self.player_x, self.player_y)
            distance = math.dist(position, self._task_target())
            detail = "Follow the gold marker" + (f"  {distance:.0f} m" if distance > 30 else "  YOU ARE HERE")
            if task[0] == "nets":
                detail += f"   WATER {self.water}%"
            elif task[0] == "lice":
                detail = f"Follow deck arrows around the pens   LICE {self.lice}%"
        self._draw_text(self.canvas, detail, (16, 63), (181, 210, 188), self.small_font)
        self._draw_minimap()
        for i, (label, color) in enumerate((("PENS", (100, 227, 211)), ("HATCHERY", (193, 223, 250)), ("MARKET", (248, 224, 145)))):
            pygame.draw.rect(self.canvas, (24, 49, 49), (551, 71 + i * 12, 78, 12))
            self._draw_text(self.canvas, label, (556, 72 + i * 12), color, self.small_font)
        if self.panel_message:
            pygame.draw.rect(self.canvas, (24, 49, 49), (8, 297, 624, 17))
            self._draw_text(self.canvas, self.panel_message, (13, 300), (255, 222, 136), self.small_font)
        pygame.draw.rect(self.canvas, (24, 49, 49), (0, 316, 640, 84))
        self._draw_text(self.canvas, f"SHAREHOLDER VALUE: {self._shareholder_value()} pts", (10, 320), (245, 211, 124), self.small_font)
        self._draw_text(self.canvas, f"MATURE {self.fish:,}  SMOLTS {self.shift_juveniles:,}  CARGO {self.truck_cargo_kg:,.1f} kg", (233, 320), (181, 210, 188), self.small_font)
        self._gold_arrow(216, 325, self.value_seconds)
        caption = self.shift_caption if self.caption_seconds > 0 else self.panel_message or "MARA: Try to impress a fish."
        speaker, _, dialogue = caption.partition(":")
        if speaker not in ("MARA", "BERNARD", "CLERK", "HEAD OFFICE"):
            speaker, dialogue = "MARA", caption
        self._draw_portrait(speaker, 10, 336)
        self._shift_lines(dialogue.strip(), 75, 342, 549)
        self._draw_text(self.canvas, "WASD move  E interact  SPACE action  H help  ESC pause  B Album  V music " + ("OFF" if self.audio_muted else "ON"), (10, 389), font=self.small_font)
        if self.effect == "calendar" and self.effect_seconds > 0:
            pygame.draw.rect(self.canvas, (239, 226, 188), (200, 198, 240, 79))
            pygame.draw.rect(self.canvas, (181, 92, 78), (200, 198, 240, 20))
            self._draw_text(self.canvas, "FARM CALENDAR / NOT MAGIC", (320, 207), (255, 245, 213), self.small_font, center=True)
            self._draw_text(self.canvas, f"WEEK {self.week}", (320, 238), (47, 78, 69), self.large_font, center=True)
            self._draw_text(self.canvas, str(self.hatchery["stage"]).replace("_", " ").upper(), (320, 263), (47, 78, 69), self.small_font, center=True)
            length = {"alevins": 12, "fry": 22, "smolt_ready": 34}.get(self.hatchery["stage"], 10)
            self._draw_fish(self.canvas, 397, 240, length, self.shift_elapsed)
            pygame.draw.line(self.canvas, (255, 244, 215), (202, 220 + int(self.effect_seconds * 17) % 54), (438, 220), 2)
        if task[0] == "done":
            self._draw_shift_receipt()
        elif self.shift_paused:
            pygame.draw.rect(self.canvas, (25, 54, 56), (130, 113, 380, 166))
            pygame.draw.rect(self.canvas, (235, 210, 147), (130, 113, 380, 166), 2)
            self._draw_text(self.canvas, "SALMON ON A BREAK", (320, 148), font=self.large_font, center=True)
            self._draw_text(self.canvas, "ENTER / ESC: Resume", (320, 197), center=True)
            self._draw_text(self.canvas, "M: Main menu (discard shift)", (320, 234), center=True)

    def _draw_shift_target(self):
        if self._task()[0] in ("done", "stamp"):
            return
        target = self._task_target()
        tx, ty = target if self.inside_hatchery else self._world_to_screen(*target)
        pulse = int(3 * math.sin(self.shift_elapsed * 4))
        pygame.draw.ellipse(self.canvas, (255, 222, 111), (tx - 16 - pulse, ty - 6, 32 + pulse * 2, 12), 2)
        if self._task_near():
            name = self._task()[0]
            control = "E + D" if name == "nets" and self.net_attached else "SPACE" if name.endswith("_weeks") or self.scoop_ready or name == "lice" and self.pump_connected or name == "grade" and self.grade_open else "E"
            if self.carrying_crate:
                control = f"E: Load crate {self.loaded_crates + 1}/3"
                pygame.draw.rect(self.canvas, (255, 222, 111), (tx - 25, ty - 23, 50, 43), 1)
            self._draw_text(self.canvas, control, (tx - 20 if self.carrying_crate else tx, ty - 27 if self.carrying_crate else ty - 15),
                            (255, 226, 145), self.small_font, center=True)
        if self.shift_hold:
            px, py = max(5, min(587, int(tx) - 24)), max(85, min(294, int(ty) - 32))
            pygame.draw.rect(self.canvas, (29, 64, 64), (px - 2, py - 2, 52, 10))
            pygame.draw.rect(self.canvas, (244, 204, 111), (px, py, round(48 * min(1, self.shift_hold / self._task()[4])), 6))
        if self.success_seconds > 0 and self.success_inside == self.inside_hatchery:
            sx, sy = self.success_point if self.inside_hatchery else self._world_to_screen(*self.success_point)
            lift = (1 - self.success_seconds) * 9
            pygame.draw.lines(self.canvas, (144, 235, 168), False,
                              [(sx - 4, sy - 15 - lift), (sx, sy - 11 - lift), (sx + 9, sy - 23 - lift)], 2)
        if not (28 < tx < 612 and 80 < ty < 300):
            # The one obstructed transition follows fixed deck corners.
            if self._task()[0] == "lice":
                guide = self._treatment_approach()
                tx, ty = self._world_to_screen(*guide)
            dx, dy = tx - 320, ty - 190
            vec = pygame.Vector2(dx, dy)
            if vec.length_squared():
                vec = vec.normalize()
                tip = pygame.Vector2(320, 190) + vec * 86
                side = pygame.Vector2(-vec.y, vec.x) * 6
                pygame.draw.polygon(self.canvas, (255, 221, 113), [tip, tip - vec * 17 + side, tip - vec * 17 - side])
        if self.in_truck:
            ux, uy = self._world_to_screen(3260, 1910)
            pygame.draw.rect(self.canvas, (250, 215, 105), (ux - 45, uy - 25, 90, 50), 2)
            self._draw_text(self.canvas, "UNLOAD HERE", (ux, uy - 35), font=self.small_font, center=True)

    def _treatment_approach(self):
        if self.player_x > 2690 and self.player_y < 1296:
            return 2760, 1300
        if self.player_x > 2440 and self.player_y >= 1275:
            return 2432, 1300
        return TASKS[4][2]

    def _gold_arrow(self, x, y, seconds):
        if seconds <= 0:
            return
        y -= int((1.4 - min(1.4, seconds)) * 9)
        pygame.draw.line(self.canvas, (250, 204, 95), (x, y + 6), (x, y - 5), 2)
        pygame.draw.polygon(self.canvas, (250, 204, 95), [(x, y - 9), (x - 4, y - 3), (x + 4, y - 3)])

    def _draw_shift_props(self):
        t = self.shift_elapsed
        if not self.inside_hatchery:
            self._draw_corporate_farm()
            # Bernard is always in pen A, never in the delivery cargo.
            x, y = self._world_to_screen(2524, 1159)
            feeding = self.effect == "feed" and self.effect_seconds > 0
            age = self.effect_duration - self.effect_seconds
            frenzy = feeding and self.shift_feed_round == 3 and age < 2.8
            bx = x + math.sin(t * (8 if frenzy else 1.5)) * (13 if feeding else 5)
            by = y + math.cos(t * 5) * 5 if feeding else y
            if feeding and self.shift_feed_round == 1 and age < 2.8:
                fx, fy = self._world_to_screen(*self.shift_feed_point)
                approach = math.sin(min(1, age / 2.8) * math.pi) * .7
                bx, by = bx + (fx - bx) * approach, by + (fy - by) * approach
            self._draw_fish(self.canvas, bx, by, 28, t, bernard=True,
                            expression=self._bernard_expression(), clipboard=not frenzy)
            self._draw_text(self.canvas, "BERNARD", (x, y - 50), (255, 225, 117), self.small_font, center=True)
            if (feeding and self.shift_feed_round < 3) or self.scoop_ready:
                wobble = round(math.sin(t * 12) * (4 if self.shift_feed_round == 2 else 1))
                self._paper_sign("STAFF ONLY" if self.shift_feed_round == 2 else "ORDERLY QUEUE", x - 125, y - 24 + wobble, 90,
                                 math.sin(t * 10) * 20 if self.shift_feed_round == 2 else 0)
                pygame.draw.line(self.canvas, (220, 190, 128), (x - 36, y - 6 + wobble), (bx - 5, by), 1)
            if self.shift_juveniles:
                # A larger rulebook replaces the little clipboard.
                pygame.draw.rect(self.canvas, (128, 74, 62), (x - 29, y + 1, 23, 24))
                pygame.draw.rect(self.canvas, (238, 222, 175), (x - 26, y + 3, 18, 19))
                self._draw_text(self.canvas, "VOL. 1", (x - 28, y + 9), (83, 81, 62), self.small_font)
                rx, ry = self._world_to_screen(2274, 1274)
                self._placard((rx, ry, 148, 29), ("FORWARD-LOOKING", "STATEMENTS / VOL. 1"))
                if self.effect == "transfer" and self.effect_seconds > 0:
                    self._paper_sign("WELCOME COMMITTEE", x - 57, y - 29, 114)
            if self._task()[0] == "drive" and self.in_truck:
                pygame.draw.line(self.canvas, (241, 220, 161), (bx + 5, by - 2), (bx + 15, by - 15 + int(math.sin(t * 3) * 2)), 2)
            if "Cleaned" in self.shift_care:
                self._draw_complaint()
            if self.truck_arrival > 0:
                x, y = self._world_to_screen(*LOADING_SPOT)
                self._draw_text(self.canvas, "MARA: TRUCK'S HERE!", (x, y - 40), font=self.small_font, center=True)
            if self._task()[0] in ("harvest", "drive"):
                x, y = self._world_to_screen(*CRATE_SPOTS[0])
                # Mara stacks, rather than conjures, the last crate.
                pygame.draw.rect(self.canvas, (222, 169, 72), (x + 27, y - 20, 10, 13))
                nod = int(math.sin(self.crate_bounce * 15) * 2) if self.loaded_crates == 3 else 0
                pygame.draw.rect(self.canvas, (236, 192, 146), (x + 29, y - 27 + nod, 6, 7))
                pygame.draw.rect(self.canvas, (181, 80, 59), (x + 27, y - 28, 10, 3))
                for i in range(3):
                    if i < self.loaded_crates or i == self.loaded_crates and self.carrying_crate:
                        continue
                    cx, cy = self._world_to_screen(*CRATE_SPOTS[i])
                    cy -= 12
                    pygame.draw.rect(self.canvas, (176, 127, 74), (cx, cy, 12, 9))
                    pygame.draw.rect(self.canvas, (233, 196, 124), (cx, cy, 12, 9), 1)
                    pygame.draw.line(self.canvas, (109, 88, 63), (cx + 5, cy), (cx + 5, cy + 8))
                if self.carrying_crate:
                    label = "YIELD-BEARING SALMON" if self.marketing_label else "SALMON"
                    self._paper_sign(label, x - 70, y - 48, 143)
                self._gold_arrow(x + 87, y - 22, self.value_seconds)
        else:
            if self.hatchery["stage"] == "eggs":
                rock = int(math.sin(t * 5) * 2)
                pygame.draw.ellipse(self.canvas, (244, 163, 83), (146 + rock, 151, 7, 9))
                pygame.draw.rect(self.canvas, (255, 211, 142), (148 + rock, 153, 2, 2))
                self._paper_sign("NEW STARTERS", 73, 190, 101)
                self._draw_text(self.canvas, "They are eggs. -Mara", (60, 212), (44, 80, 69), self.small_font)
            if self.shift_task >= 8:
                dot_y = 87 + int(t * 26) % 55
                pygame.draw.rect(self.canvas, (104, 206, 191), (204, dot_y, 3, 5))
                pygame.draw.circle(self.canvas, (109, 207, 194), (221, 143), 2, 1)
                self._placard((57, 82, 145, 17), ("LIQUIDITY IMPROVED",))
            if self.effect == "nursery" and self.effect_seconds > 0:
                self._paper_sign("STAFF MEETING", 256, 200, 98)
                for i in range(4):
                    pygame.draw.circle(self.canvas, (238, 199, 106), (251 + i * 21, 102 + int(math.sin(t * 3 + i) * 3)), 1)
            if self.shift_screened:
                self._draw_text(self.canvas, "SCREEN: CLEAR", (495, 185), (31, 66, 55), self.small_font, center=True)
            if self.hatchery["vaccinated"]:
                self._draw_text(self.canvas, "VACCINE: COMPLETE", (495, 198), (31, 66, 55), self.small_font, center=True)
                self._draw_fish(self.canvas, 492, 115, 30, t)
                pygame.draw.circle(self.canvas, (248, 204, 91), (513, 117), 5)
                self._placard((431, 82, 136, 17), ("ASSET PROTECTION",))
                self._draw_text(self.canvas, "BRAVE", (534, 119), (242, 218, 153), self.small_font, center=True)
            if self.shift_held_back:
                self._draw_text(self.canvas, f"{self.shift_held_back} BACK TO NURSERY", (485, 289), (31, 66, 55), self.small_font, center=True)
            if self.effect == "grade" and self.effect_seconds > 0:
                for i in range(6):
                    x = 405 + (i * 17 + int(t * 40)) % 155
                    self._draw_fish(self.canvas, x, 234 + i % 2 * 10, 13, t + i)
                pygame.draw.line(self.canvas, (63, 135, 139), (420, 226), (350, 183), 9)
                for i in range(3):
                    progress = (t * .7 + i / 3) % 1
                    self._draw_fish(self.canvas, 420 - progress * 70, 226 - progress * 43, 10, t, facing=-1)
                self._paper_sign("LONG-TERM INVESTMENT", 278, 211, 139)
        self._draw_action_props()
        self._draw_market_scene()
        if self.effect_seconds <= 0:
            return
        if self.effect == "feed":
            x, y = self._world_to_screen(*self.shift_feed_point)
            for i in range(14):
                phase = (t * 1.2 + i / 14) % 1
                pygame.draw.rect(self.canvas, (240, 210, 121), (x - 24 + i * 4, y - int(math.sin(phase * math.pi) * 33), 2, 2))
                pygame.draw.circle(self.canvas, (183, 239, 225), (x - 20 + i * 3, y - 30), 2 + int(phase * 4), 1)
        elif self.effect == "lice":
            x, y = self._world_to_screen(2432, 1185)
            x -= int((self.effect_duration - self.effect_seconds) * 9)
            pygame.draw.circle(self.canvas, (126, 78, 87), (x, y - 24), 4)
            for offset in (-4, 4):
                pygame.draw.line(self.canvas, (126, 78, 87), (x + offset, y - 23), (x + offset * 2, y - 16), 1)
            pygame.draw.rect(self.canvas, (173, 125, 73), (x + 8, y - 23, 9, 7))
            pygame.draw.rect(self.canvas, (100, 82, 66), (x + 10, y - 26, 5, 3), 1)
            self._paper_sign("CONTRACT NOT RENEWED", x - 137, y - 58, 145)
            self._draw_text(self.canvas, "EXTERNAL CONSULTANT", (x - 125, y - 36), (255, 230, 164), self.small_font)
        elif self.effect == "vaccine":
            pygame.draw.line(self.canvas, (83, 174, 118), (491, 104), (499, 113), 3)
            pygame.draw.line(self.canvas, (83, 174, 118), (499, 113), (517, 91), 3)

    def _paper_sign(self, text, x, y, width, angle=0):
        sign = pygame.Surface((width + 2, 18), pygame.SRCALPHA)
        pygame.draw.rect(sign, (91, 91, 66), (1, 2, width, 15))
        pygame.draw.rect(sign, (243, 224, 170), (0, 0, width, 15))
        self._draw_text(sign, text, (width // 2, 7), (49, 76, 65), self.small_font, center=True)
        if angle:
            sign = pygame.transform.rotate(sign, angle)
        self.canvas.blit(sign, sign.get_rect(center=(x + width // 2, y + 9)))

    def _placard(self, rect, lines):
        x, y, w, h = rect
        pygame.draw.rect(self.canvas, (24, 44, 66), rect)
        pygame.draw.rect(self.canvas, (190, 166, 102), rect, 1)
        pygame.draw.line(self.canvas, (69, 91, 112), (x + 2, y + 2), (x + w - 3, y + 2))
        for i, line in enumerate(lines):
            self._draw_text(self.canvas, line, (x + w // 2, y + 8 + i * 12), (241, 215, 153), self.small_font, center=True)

    def _draw_corporate_farm(self):
        x, y = self._world_to_screen(2274, 1104)
        self._placard((x, y, 148, 87), ("TIDE & TACKLE", "INVESTOR RELATIONS"))
        self._draw_text(self.canvas, "ILLUSTRATIVE ENTHUSIASM", (x + 74, y + 77), (184, 205, 203), self.small_font, center=True)
        pygame.draw.rect(self.canvas, (66, 91, 111), (x + 8, y + 29, 132, 40), 1)
        pygame.draw.lines(self.canvas, (88, 111, 127), False, [(x + 12, y + 34), (x + 12, y + 66), (x + 135, y + 66)], 1)
        rise = self._shareholder_value() / 100
        points = [(x + 15, y + 62), (x + 43, y + 58), (x + 67, y + 63 - rise * 28), (x + 99, y + 55 - rise * 32)]
        if "Cleaned" in self.shift_care:
            points += [(x + 131, y + 30), (x + 140, y + 30), (x + 136, y + 39)]
        else:
            points += [(x + 132, y + 45 - rise * 15)]
        pygame.draw.lines(self.canvas, (247, 205, 100), False, points, 2)
        ex, ey = points[-1]
        pygame.draw.polygon(self.canvas, (247, 205, 100), [(ex, ey), (ex - 5, ey - 3), (ex + 2, ey - 6)])
        if self.effect == "transfer" and self.effect_seconds > 0:
            self._draw_fish(self.canvas, x + 121, y + 55, 25, self.shift_elapsed, bernard=True)
            pygame.draw.line(self.canvas, (225, 211, 157), (x + 123, y + 47), (ex, ey), 2)
        x, y = self._world_to_screen(2274, 1200)
        self._placard((x, y, 148, 48), ("OUR PRIORITIES", "1. SHAREHOLDER VALUE", "2. SEE PRIORITY ONE"))
        self._paper_sign("Feed the salmon. -Mara", x, y + 51, 148)
        if self._task()[0] == "lice":
            for wx, wy, dx, dy in ((2760, 1237, 0, 1), (2737, 1300, -1, 0), (2590, 1300, -1, 0), (2440, 1265, 0, -1)):
                ax, ay = self._world_to_screen(wx, wy)
                v, side = pygame.Vector2(dx, dy), pygame.Vector2(-dy, dx)
                center = pygame.Vector2(ax, ay)
                pygame.draw.line(self.canvas, (242, 219, 150), center - v * 10, center + v * 5, 3)
                pygame.draw.polygon(self.canvas, (242, 219, 150), [center + v * 12, center + side * 6, center - side * 6])

    def _draw_work_pose(self, x, y):
        task, t = self._task()[0], self.shift_elapsed
        if self.carrying_crate:
            pygame.draw.rect(self.canvas, (182, 137, 83), (x - 10, y - 14, 20, 13))
            pygame.draw.rect(self.canvas, (238, 205, 141), (x - 10, y - 14, 20, 13), 1)
            pygame.draw.line(self.canvas, (110, 85, 60), (x, y - 14), (x, y - 2), 2)
        elif self.scoop_ready or self.throw_age < .45:
            swing = math.sin(min(1, self.throw_age / .45) * math.pi) * 12 if not self.scoop_ready else 0
            pygame.draw.line(self.canvas, (235, 189, 145), (x + 3, y - 5), (x + 12, y - 9 - swing), 3)
            pygame.draw.line(self.canvas, (173, 138, 83), (x + 10, y - 8 - swing), (x + 21, y - 13 - swing), 2)
            pygame.draw.ellipse(self.canvas, (217, 204, 160), (x + 17, y - 17 - swing, 8, 5))
        elif task == "nets" and self.net_attached:
            nx, ny = self._world_to_screen(*TASKS[3][2])
            pygame.draw.line(self.canvas, (214, 181, 123), (x - 7, y - 4), (nx - 30, ny - 10), 3)
            pygame.draw.line(self.canvas, (236, 192, 147), (x + 3, y - 7), (x - 7, y - 4), 3)
        elif task == "lice" and self.pump_connected:
            offset = math.sin(t * 13) * 4 if pygame.K_SPACE in self.held_keys else 0
            pygame.draw.line(self.canvas, (236, 192, 147), (x, y - 4), (x - 13, y - 13 + offset), 3)
        elif task == "flow" and pygame.K_e in self.held_keys:
            pygame.draw.circle(self.canvas, (208, 164, 95), (x + 12, y - 12), 7, 2)
            pygame.draw.line(self.canvas, (208, 164, 95), (x + 12, y - 12),
                             (x + 12 + int(math.cos(t * 5) * 6), y - 12 + int(math.sin(t * 5) * 6)), 2)
            pygame.draw.line(self.canvas, (236, 192, 147), (x, y - 5), (x + 12, y - 12), 3)

    def _draw_action_props(self):
        task, t = self._task()[0], self.shift_elapsed
        if not self.inside_hatchery:
            if task.startswith("feed"):
                x, y = self._world_to_screen(*self._task_target())
                pygame.draw.rect(self.canvas, (116, 135, 115), (x - 18, y - 4, 11, 9))
                pygame.draw.polygon(self.canvas, (177, 192, 157), [(x - 18, y + 1), (x - 7, y + 1), (x - 13, y - 13)])
                if self.feed_spill:
                    for i in range(16):
                        pygame.draw.rect(self.canvas, (242, 204, 108), (x - 10 + i * 5 % 23, y - 4 + i * 7 % 9, 2, 2))
                    self._paper_sign("WASTE REDUCTION", x - 53, y - 34, 106)
                elif self.scoop_ready:
                    landing, good = self._feed_preview()
                    lx, ly = self._world_to_screen(*landing)
                    for i in range(1, 8):
                        gx = x + (lx - x) * i / 8
                        gy = y + (ly - y) * i / 8
                        pygame.draw.circle(self.canvas, (154, 224, 165) if good else (242, 189, 109), (round(gx), round(gy)), 2)
                    pygame.draw.ellipse(self.canvas, (154, 224, 165) if good else (242, 189, 109), (lx - 13, ly - 5, 26, 10), 2)
            if self.throw_pending:
                sx, sy = self._world_to_screen(*self.throw_origin)
                ex, ey = self._world_to_screen(*self.throw_point)
                p = min(1, self.throw_age / .45)
                for i in range(8):
                    px, py = sx + (ex - sx) * p + (i - 4) * 2, sy + (ey - sy) * p - (0 if self.throw_recovery else math.sin(p * math.pi) * 28) + i % 3
                    pygame.draw.rect(self.canvas, (239, 205, 119), (px, py, 2, 2))
            nx, ny = self._world_to_screen(*TASKS[3][2])
            if "Cleaned" not in self.shift_care:
                pygame.draw.ellipse(self.canvas, (71, 101, 70), (nx - 32, ny - 15, 26, 22))
                if self.net_attached and pygame.K_e not in self.held_keys:
                    self._draw_text(self.canvas, "BERNARD: HOLDING IT!", (nx, ny - 53), (248, 227, 166), self.small_font, center=True)
            px, py = self._world_to_screen(*TASKS[4][2])
            pygame.draw.rect(self.canvas, (78, 132, 130), (px - 20, py - 14, 13, 20))
            pygame.draw.lines(self.canvas, (172, 185, 143), False, [(px - 14, py - 14), (px - 14, py - 24), (px - 23, py - 24)], 3)
            if self.pump_connected:
                pygame.draw.lines(self.canvas, (66, 105, 105), False, [(px - 6, py), (px + 7, py + 9), (px + 29, py + 4)], 3)
                pygame.draw.circle(self.canvas, (226, 211, 161), (px - 14, py - 5), 5)
                pygame.draw.line(self.canvas, (85, 150, 103), (px - 14, py - 5), (px - 14 + int(self.pump_progress * 2), py - 9), 1)
        else:
            if self._task()[0] == "alevins":
                pygame.draw.polygon(self.canvas, (112, 131, 78), [(225, 141), (234, 138), (238, 143), (229, 147)])
            elif self.effect == "nursery" and self.effect_seconds > 0 and self.shift_task == 10:
                age = self.effect_duration - self.effect_seconds
                pygame.draw.rect(self.canvas, (112, 131, 78), (225 - min(45, age * 22), 141, 8, 4))
            if self._task()[0] == "vaccine" and self.shift_hold:
                pygame.draw.rect(self.canvas, (67, 135, 139), (432, 128, 126, 15))
                for i in range(4):
                    self._draw_fish(self.canvas, 438 + (t * 32 + i * 28) % 112, 135, 11, t + i)
            if self.screen_started and task == "screen":
                for i, label in enumerate(("WATER", "CONDITION", "READINESS")):
                    ready = self.screen_timer <= 1.5 - (i + 1) * .5
                    self._draw_text(self.canvas, ("[x] " if ready else "[ ] ") + label, (423, 204 + i * 13),
                                    (37, 111, 75) if ready else (94, 119, 102), self.small_font)
            if task == "grade" and self.grade_open:
                pygame.draw.rect(self.canvas, (35, 76, 77), (412, 191, 148, 22))
                pygame.draw.rect(self.canvas, (96, 177, 121), (449, 197, 74, 10))
                pygame.draw.line(self.canvas, (252, 215, 112), (412 + self.grade_guide * 148, 192), (412 + self.grade_guide * 148, 212), 3)
                for i in range(5):
                    self._draw_fish(self.canvas, 414 + (t * 40 + i * 25) % 142, 237 + i % 2 * 10, 12, t + i)
                if self.grade_retry:
                    self._paper_sign("PLEASE TRY AGAIN", 397, 174, 134)
            if task == "transfer" and self.transfer_connected:
                pygame.draw.rect(self.canvas, (44, 99, 107), (397, 225, 170, 30))
                pygame.draw.rect(self.canvas, (80, 176, 168), (400, 227, int(164 * self.transfer_progress), 26))
                for i in range(8):
                    if self.transfer_started:
                        self._draw_fish(self.canvas, 402 + (t * 50 + i * 19) % 160, 234 + i % 2 * 12, 10, t)
                # Live view of pen D: the new school stays at the farm.
                pygame.draw.rect(self.canvas, (41, 83, 86), (50, 224, 137, 73))
                self._draw_text(self.canvas, "PEN D / JUVENILES", (57, 232), font=self.small_font)
                pygame.draw.ellipse(self.canvas, (48, 140, 146), (66, 249, 103, 37))
                for i in range(min(8, int(self.transfer_progress * 9))):
                    self._draw_fish(self.canvas, 80 + i * 10, 265 + math.sin(t + i) * 5, 9, t + i)
            if task == "alevin_weeks":
                self._draw_text(self.canvas, "[x] INTAKE CLEAR", (214, 192), (37, 111, 75), self.small_font)
            if task == "fry_weeks":
                self._draw_text(self.canvas, "[x] FED / OUTLET CLEAR", (254, 192), (37, 111, 75), self.small_font)
            if not self._task_near():
                station = self._nearest_hatchery_station()
                if station and station[1] < 55:
                    sx, sy = self.interior_x, self.interior_y
                    target = pygame.Vector2(self._task_target()) - pygame.Vector2(sx, sy)
                    if target.length_squared():
                        v = target.normalize()
                        end = pygame.Vector2(sx, sy) + v * 25
                        side = pygame.Vector2(-v.y, v.x) * 4
                        pygame.draw.polygon(self.canvas, (245, 208, 111), [end, end - v * 10 + side, end - v * 10 - side])

    def _draw_market_scene(self):
        if self.inside_hatchery:
            return
        for wx, wy, text in ((2808, 1360, "MARKET ->"), (3095, 1665, "FISH MARKET ->")):
            x, y = self._world_to_screen(wx, wy)
            self._paper_sign(text, x, y - 22, 100)
            pygame.draw.line(self.canvas, (144, 112, 75), (x + 50, y - 7), (x + 50, y + 4), 2)
        x, y = self._world_to_screen(3308, 1915)
        pygame.draw.rect(self.canvas, (155, 117, 78), (x - 12, y - 7, 98, 38))
        for offset in range(0, 96, 12):
            pygame.draw.line(self.canvas, (202, 164, 106), (x - 10 + offset, y - 7), (x - 10 + offset, y + 30))
        pygame.draw.rect(self.canvas, (82, 113, 114), (x + 21, y - 29, 12, 18))
        pygame.draw.rect(self.canvas, (235, 190, 145), (x + 24, y - 37, 7, 8))
        pygame.draw.rect(self.canvas, (55, 78, 82), (x + 21, y - 39, 13, 4))
        pygame.draw.rect(self.canvas, (238, 222, 177), (x + 44, y - 12, 22, 13))
        pygame.draw.line(self.canvas, (124, 145, 119), (x + 54, y - 12), (x + 54, y + 1))
        self._paper_sign("SALMON DELIVERIES", x - 22, y - 66, 155)
        self._draw_text(self.canvas, "HUMANS MAY ACCOMPANY", (x - 10, y - 45), (247, 225, 167), self.small_font)
        task = self._task()[0]
        if task != "stamp":
            return
        for i in range(3):
            pygame.draw.rect(self.canvas, (204, 165, 100), (x + i * 19, y + 4, 17, 13))
        weight = self.truck_cargo_kg * (1 - self.market_timer / 1.8) if self.market_phase == "weigh" else self.truck_cargo_kg
        pygame.draw.rect(self.canvas, (27, 66, 65), (x - 11, y + 22, 100, 15))
        self._draw_text(self.canvas, f"{weight:,.1f} kg", (x - 4, y + 25), (154, 228, 174), self.small_font)
        if self.market_phase == "weigh":
            return
        height = 125 if self.market_phase == "signature" else min(220, 125 + int(self.form_age * 150))
        pygame.draw.rect(self.canvas, (37, 61, 60), (202, 94, 244, height))
        pygame.draw.rect(self.canvas, (239, 226, 187), (198, 90, 244, height))
        self._draw_text(self.canvas, "MARKET AUTHORIZATION", (320, 105), (37, 76, 69), center=True)
        self._draw_text(self.canvas, "Human signature:", (214, 130), (37, 76, 69), self.small_font)
        pygame.draw.lines(self.canvas, (96, 113, 113), False, [(216, 152), (251, 137), (244, 159), (282, 144), (309, 151)], 1)
        pygame.draw.line(self.canvas, (179, 83, 69), (212, 140), (313, 161), 2)
        self._draw_text(self.canvas, "REJECTED", (348, 151), (179, 83, 69), self.small_font)
        if self.market_phase == "signature":
            self._draw_text(self.canvas, "SPACE: Unfold Bernard's short form", (210, 186), (37, 76, 69), self.small_font)
        else:
            for line_y in range(177, min(277, 88 + height), 19):
                pygame.draw.line(self.canvas, (198, 190, 153), (214, line_y), (427, line_y))
            if height >= 207:
                self._draw_text(self.canvas, "ONE WET FINPRINT REQUIRED", (320, 245), (37, 76, 69), self.small_font, center=True)
                self._draw_text(self.canvas, "E: Place Bernard's authorization", (210, 283), (37, 76, 69), self.small_font)

    def _draw_complaint(self):
        x, y = self._world_to_screen(2792, 1103)
        t = self.shift_elapsed
        age = self.effect_duration - self.effect_seconds if self.effect == "paper" else 10
        height = min(186, 18 + int(age * 36))
        x += int(math.sin(t * 3) * 2)
        pygame.draw.rect(self.canvas, (77, 88, 66), (x + 2, y + 3, 94, height))
        pygame.draw.rect(self.canvas, (238, 226, 182), (x, y, 94, height))
        for row, line in enumerate(("COMPLAINT", "EVERYTHING", "IS WET.", "THE WATER IS", "OUTSIDE.", "THE WATER IS", "ALSO INSIDE.", "PLEASE ADVISE.")):
            if row * 13 + 13 < height:
                self._draw_text(self.canvas, line, (x + 6, y + 5 + row * 13), (58, 83, 71), self.small_font)
        if height > 175:
            self._placard((x + 3, y + 112, 88, 70), ("WATER QUALITY", "IS NOT A", "SUBSTITUTE FOR", "QUARTERLY", "GUIDANCE."))
        for drop in range(3):
            pygame.draw.line(self.canvas, (104, 194, 204), (x + 10 + drop * 32, y + height),
                             (x + 10 + drop * 32, y + height + 3 + int((t * 9 + drop * 3) % 7)), 1)

    def _draw_coastal_details(self):
        t = self._art_time()
        x, y = self._world_to_screen(2458, 1125)
        pygame.draw.line(self.canvas, (228, 207, 156), (x, y), (x, y - 37), 2)
        flutter = int(math.sin(t * 4) * 3)
        pygame.draw.polygon(self.canvas, (223, 131, 88), [(x, y - 36), (x + 25, y - 31 + flutter), (x + 25, y - 26 + flutter), (x, y - 26)])
        pygame.draw.line(self.canvas, (242, 218, 170), (x + 10, y - 33), (x + 10, y - 27), 3)
        for wx, wy in ((2508, 1234), (2646, 1152)):
            x, y = self._world_to_screen(wx, wy)
            y += round(math.sin(t * 2 + wx) * 2)
            pygame.draw.ellipse(self.canvas, (104, 196, 188), (x - 5, y + 2, 10, 4), 1)
            pygame.draw.rect(self.canvas, (234, 155, 83), (x - 2, y - 4, 5, 8))
            pygame.draw.line(self.canvas, (248, 225, 182), (x - 2, y), (x + 2, y), 2)
        x, y = self._world_to_screen(2703, 1260)
        for r in (3, 5, 7):
            pygame.draw.ellipse(self.canvas, (214, 184, 127), (x - r, y - r // 2, r * 2, r), 1)
        for wx, wy in ((2420, 1135), (2740, 1160), (2790, 1290), (2490, 1301)):
            x, y = self._world_to_screen(wx, wy)
            for i in range(4):
                pygame.draw.line(self.canvas, (81, 129, 87), (x + i * 3, y), (x + i * 3 - 2, y - 5 - i % 2 * 3))
        if self.mode == "shift":
            if self.in_truck:
                gx, gy = self.truck_x, self.truck_y - 23
            elif self.harvest_prepared:
                gx, gy = LOADING_SPOT[0], LOADING_SPOT[1] - 23
            else:
                gx, gy = TASKS[min(2, self.shift_feed_round)][2]
                gx, gy = gx + 33, gy - 12
            x, y = self._world_to_screen(gx, gy)
            facing = -1 if self.honk_seconds else 1
            pygame.draw.ellipse(self.canvas, (235, 232, 202), (x - 6, y - 5, 13, 8))
            pygame.draw.rect(self.canvas, (240, 235, 209), (x + facing * 5 - 2, y - 9, 5, 6))
            pygame.draw.line(self.canvas, (227, 175, 89), (x + facing * 7, y - 5), (x + facing * 11, y - 5), 2)
            pygame.draw.line(self.canvas, (158, 128, 81), (x, y + 3), (x - 2, y + 7), 1)
            if self.harvest_prepared:
                pygame.draw.rect(self.canvas, (246, 213, 113), (x - 3, y, 7, 6))
                self._draw_text(self.canvas, "51%" if self._task()[0] == "done" else "V", (x - 1, y), (62, 85, 69), self.small_font)
            if self.honk_seconds:
                self._paper_sign("VISITOR", x + 13, y - 16, 55)
        else:
            x, y = self._world_to_screen(2320 + (t * 19) % 650, 1090 + math.sin(t * .5) * 14)
            wing = int(math.sin(t * 7) * 3)
            pygame.draw.lines(self.canvas, (244, 235, 200), False, [(x - 7, y - wing), (x, y), (x + 7, y - wing)], 2)

    def _draw_shift_receipt(self):
        self.canvas.fill((26, 59, 61))
        pygame.draw.rect(self.canvas, (15, 41, 47), (44, 14, 564, 382))
        pygame.draw.rect(self.canvas, (238, 225, 188), (38, 8, 564, 382))
        ink = (39, 76, 67)
        for y in range(16, 385, 12):
            for x in (43, 597):
                pygame.draw.circle(self.canvas, (26, 59, 61), (x, y), 2)
        self._draw_text(self.canvas, "COLDWATER MARKET / RECEIPT", (342, 25), ink, center=True)
        self._draw_text(self.canvas, "ACTUAL WORK", (160, 46), ink, self.small_font)
        elapsed = f"{int(self.shift_elapsed) // 60}:{int(self.shift_elapsed) % 60:02d} active"
        self._draw_text(self.canvas, elapsed, (576 - self.small_font.size(elapsed)[0], 46), ink, self.small_font)
        rows = (("Mature salmon delivered", f"334 / {self.harvested_kg:,.1f} kg"),
                ("Delivery revenue", f"${self.shift_revenue:,.2f}"),
                ("Replacement smolts transferred", f"{self.shift_juveniles:,}"),
                ("Farm care completed", " / ".join(sorted(self.shift_care))),
                ("Driving bumps", str(self.shift_bumps)),
                ("Review", self._shift_review()))
        for i, (label, value) in enumerate(rows):
            y = 65 + i * 19
            font = self.small_font if i in (3, 5) else self.font
            self._draw_text(self.canvas, label, (62, y), ink, font)
            self._draw_text(self.canvas, value, (576 - font.size(value)[0], y), ink, font)
            pygame.draw.line(self.canvas, (211, 202, 163), (62, y + 15), (576, y + 15))
        self._placard((54, 183, 532, 88), ("CORPORATE INTERPRETATION",))
        corporate = (("Shareholder value", f"{self._shareholder_value()} pts"),
                     ("Credit claimed by Head Office", "100%"),
                     ("Majority shareholder", "The gull, 51%"),
                     ("Your bonus", "An enhanced sense of purpose"))
        for i, (label, value) in enumerate(corporate):
            y = 207 + i * 15
            self._draw_text(self.canvas, label, (64, y), (184, 205, 203), self.small_font)
            self._draw_text(self.canvas, value, (480 - self.small_font.size(value)[0], y), (247, 217, 148), self.small_font)
        self._draw_shareholder_gull(540, 237)
        self._shift_lines("MARA: Good shift. He doesn't stamp for just anybody.", 163, 279, 417, ink, self.small_font, 12)
        self._shift_lines("BERNARD: Shareholder value delivered. Salmon also attended to.", 163, 299, 417, ink, self.small_font, 12)
        self._shift_lines("HEAD OFFICE: " + HQ_LINES["stamp"], 163, 322, 417, ink, self.small_font, 12)
        pygame.draw.rect(self.canvas, (137, 106, 65), (66, 280, 81, 39))
        pygame.draw.rect(self.canvas, (246, 235, 201), (69, 283, 75, 33))
        self._draw_text(self.canvas, "CERTIFICATE", (107, 294), ink, self.small_font, center=True)
        self._draw_text(self.canvas, "COMPETENT", (107, 307), ink, self.small_font, center=True)
        glance = 2.3 < self.receipt_age < 3.1
        self._draw_fish(self.canvas, 106, 334, 58, self.receipt_age, facing=-1 if glance else 1,
                        bernard=True, expression="suspicious", clipboard=True)
        self._draw_text(self.canvas, "Delivery accepted. Management remains under review.", (320, 350), ink, self.small_font, center=True)
        self._draw_text(self.canvas, "B: Album / V: music", (320, 361), ink, self.small_font, center=True)
        self._draw_text(self.canvas, "ENTER: Another Shift     M / ESC: Main Menu", (320, 373), ink, center=True)
        # Crooked, heavy approval stamp and wet finprint land once.
        stamp = pygame.Surface((99, 33), pygame.SRCALPHA)
        teal = (41, 132, 136)
        pygame.draw.ellipse(stamp, teal, (1, 2, 76, 27), 2)
        self._draw_text(stamp, "APPROVED", (39, 15), teal, self.small_font, center=True)
        pygame.draw.polygon(stamp, teal, [(80, 17), (94, 2), (91, 20), (97, 29)])
        pygame.draw.circle(stamp, teal, (92, 31), 1)
        progress = min(1, self.receipt_age / .35)
        stamp = pygame.transform.rotate(stamp, -8)
        stamp.set_alpha(int(255 * progress))
        self.canvas.blit(stamp, stamp.get_rect(center=(104, 33 - int((1 - progress) * 20))))

    def _draw_shareholder_gull(self, x, y):
        # The visitor badge turns over after approval. No extra task or trip.
        t = self.receipt_age
        pygame.draw.ellipse(self.canvas, (238, 235, 207), (x - 22, y - 13, 38, 23))
        pygame.draw.ellipse(self.canvas, (170, 190, 184), (x - 19, y - 7, 25, 11))
        pygame.draw.rect(self.canvas, (245, 238, 215), (x + 7, y - 26, 14, 20))
        pygame.draw.circle(self.canvas, (40, 60, 65), (x + 17, y - 22), 2)
        pygame.draw.polygon(self.canvas, (234, 177, 77), [(x + 21, y - 18), (x + 33, y - 14), (x + 21, y - 13)])
        for offset in (-10, 4):
            pygame.draw.line(self.canvas, (222, 169, 80), (x + offset, y + 9), (x + offset, y + 19), 2)
        width = 26 if t < .5 or t > 1.1 else max(2, int(26 * abs(math.cos((t - .5) / .6 * math.pi))))
        pygame.draw.rect(self.canvas, (245, 210, 104), (x - 8 - width // 2, y - 9, width, 15))
        if width > 18:
            self._draw_text(self.canvas, "51%" if t > .8 else "V", (x - 8, y - 2), (40, 60, 65), self.small_font, center=True)
        if t > 1.1:
            pygame.draw.polygon(self.canvas, (38, 62, 92), [(x + 11, y - 7), (x + 16, y - 7), (x + 19, y + 5), (x + 14, y + 9), (x + 10, y + 5)])

    def _shift_review(self):
        if self.shift_bumps >= 3:
            return "Excellent husbandry. Ambitious parking."
        if self.feed_spills:
            return "Excellent recovery. Questionable scoop technique."
        return "Employee of the Salmon"
