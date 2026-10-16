# Tide & Tackle: Delivering Shareholder Value Since Lunch

A pixel-art salmon-farming game. Feed salmon, raise their replacements, deliver mature fish, and try to impress Bernard, the salmon committee representative.

Bernard is assessing your performance. Head Office is claiming credit. Aim scoops into a feeding frenzy, pull a comically long complaint out of the nets, operate the treatment pump, raise a replacement batch, carry three mature-fish crates to the truck, and deliver them to a clerk who requires one wet finprint. The visitor-badged gull has a surprising financial interest. The five chapters remain Care, Hatchery, Certification, Delivery, and Market.

The shareholder-value indicator is corporate enthusiasm, measured in points. It comes directly from completed farm tasks and reaches 100 after delivery; it is neither money nor a share price. The investor-relations graph, management placards, and four Head Office radio interventions reinterpret ordinary husbandry as financial genius. The receipt separates your actual work and **$10,100.16 delivery revenue** from the corporate credit claim.

## Run

On Windows, open the game folder in File Explorer and **double-click `Play Salmon.bat`**. No PowerShell or typed commands are needed. The launcher uses a local `.venv`, installs missing game packages on first launch, and starts the game. Python must already be installed; the initial package installation needs internet. Leave the launcher's window open behind the game; it closes when you quit normally and shows error details if something goes wrong.

For a downloaded ZIP, extract the entire folder before opening the launcher. Keep the `Songs` folder and MP4 beside the game files. You can right-click `Play Salmon.bat` and choose **Show more options > Send to > Desktop (create shortcut)** for a desktop launch icon.

Alternatively, from PowerShell:

```powershell
Set-Location "C:\Users\jon-e\Documents\SalmonFarmerGame"
python -m pip install -r requirements.txt
python salmon_farm.py
```

Choose with Up/Down and Enter on the title screen.

## The Salmon Album

A random MP3 from `Songs` starts automatically on the title screen at 65% volume. When it ends, another song is chosen randomly, excluding the one that just played. Music continues across menus, shift restarts, results, and career mode.

Press `B` on the title screen or during play to open the album. Use Up/Down and Enter, or click a song, to play it from the beginning. Selecting a song automatically closes the album and resumes the short shift, so you can play while listening. On the title screen it returns to the title with music playing. The current song is marked with `>`. Choose **Stop Music** for silence until you select another song. Opening the album pauses gameplay and the active shift timer while allowing you to listen. `B` or `Esc` closes it without choosing a song and preserves the previous pause state. The video option opens its separate viewing screen.

Press `V` to mute/unmute music. Muted playback still advances. Regular shift pause and losing window focus pause the music at its current position. Playback and mute preferences last only for the current application session.

**The album is the game's only audio.** Effects, horns, ambience, and notification sounds are silent; their visual reactions remain. Unreadable songs are skipped for the session. If only one playable song remains, it repeats. Missing songs or unavailable audio hardware leave the game playable in silence.

MP3s are discovered once at startup relative to the game's own `Songs` folder, so launching from another working directory also works. Underscores become spaces in displayed titles. Restart the game after adding files.

Select **VIDEO: Superstar + Whispers (15s delay)** in the album. **Whispers of a Dusk Breeze** starts immediately. After **15 seconds of the song**, `salmon_superstar_final.mp4` starts from **0:00**, with the song continuing alongside it. A countdown appears during the music intro; none of the video is skipped. The video's original audio is muted. This is an optional viewing screen that pauses gameplay and the active shift timer.

During the video, `Space` pauses/resumes both picture and song, `V` mutes/unmutes the song, and `Esc` or `B` returns to the album. Losing focus pauses both. The video returns to the album when finished; Whispers continues playing. MP4 playback uses the PyAV dependency from `requirements.txt`, so run the installation command above after updating the game.

## Five-Minute Salmon Shift

A complete, forgiving little story, intended for about 4–6 minutes on a first visit. There is no countdown. Take longer if you like. Supplies and treatments are prepaid; the committee's complaints are complimentary.

1. Start beside four large net pens. At each gold feeding spot, `E` takes a scoop, `A/D` aims, and `Space` throws. The landing circle is green for a successful throw and amber for a spill. Pellets fly for about 0.45 seconds; feeding credit, the splash, and the fish rush happen on impact. You can move during the throw. If pellets spill, `E` sweeps them down the chute for no extra feed or duplicate points. `E` also puts a scoop down so you can walk again.
2. At the net pole, press `E`, then hold `E` and `D`/Right to pull backward. Releasing pauses your work; it does not lose progress. At the lice station, `E` connects the hose and holding `Space` operates the pump. Pump progress also stays when released.
3. Enter the hatchery. `E` receives fertilized eggs; hold `E` at the valve to restore intake flow. Confirm the labeled two-week, two-week, and three-week skips with `Space`. Inspect and clear the alevin intake with `E`; feed fry with `Space`, then clean their outlet with `E`.
4. `E` starts the health screen; hold `E` to vaccinate. At the grader, `E` opens/closes the flume, `A/D` positions the guide in the green band, and `Space` confirms. Wrong positions loop the fish safely around. `E` connects the transfer line; `Space` opens it. The small salmon visibly transfer to pen D and stay at the farm.
5. Back beside the pens, `E` prepares 334 **mature** salmon in three crates. Walk to each gold-marked crate and press `E` to carry; walk to the outlined truck bed and press `E` to load. While carrying, `Space` flips the label between SALMON and YIELD-BEARING SALMON. This optional marketing changes no weight, price, or points. Carrying does not slow walking. The full delivery is 1,202.4 kg; Bernard stays at the farm.
6. Drive to the marked market yard, stop, and press `E` to unload. Watch the receiving scale. `Space` unfolds Bernard's authorization, and `E` places the finprint. Your final review reflects recovered feed spills and rough parking, with an approving word from Mara.

Controls:

- `WASD` / arrows: walk or drive; `Shift`: run on foot.
- `E` / `Space`: follow the current action prompt; `A/D` aims the scoop or grading guide while those tools are open. `Space` flips a carried crate's marketing label. The prompt beside each station gives its current operation.
- Driving: `W` accelerates, `S` brakes then reverses, `A/D` steers, `Space` honks, and `E` enters/exits when parked or unloads at market. Follow the gold arrow and roadside market signs. Wrong turns and bumps do not spoil your cargo.
- `H`: get unstuck at a safe approach to the current task. While driving, this returns the truck to the delivery's starting position; it does not complete the delivery.
- `Esc`: pause/resume. In the pause screen, `Enter` resumes and `M` returns to the title. Losing window focus pauses the shift too.
- `B`: open/close the album and choose a song or Stop Music.
- `V`: mute/unmute music. All other sounds stay silent.
- On the receipt: `Enter` starts another shift; `M` or `Esc` returns to the title.

**Short shifts are entirely in memory.** Returning to the title or closing the game discards the shift. F5/F9 do not save or load anything in this mode. Career files are never read or written by a short shift.

## Farm Career

The existing open-ended island career remains available from the title screen. Explore on foot, operate the pens and hatchery, buy feed, improve the farm, and drive deliveries through the same world. Other destinations include the feed mill, workshop, research station, fishing spots, town, and forest trail.

The pens are northeast of the starting farm yard. Follow the farm objective or teal minimap marker and press `E` nearby. Visit the blue-marked hatchery to enter its walkable incubator, nursery, health lab, and grading stations. Use station number keys to work; advance farm weeks at the rest house. Vaccinated, graded smolts can then transfer into pen stock.

Career controls:

- `WASD` / arrows: walk or drive; `Shift`: run; `E`: interact or enter/exit the truck.
- `M`: island map; `J`: journal, contract, inventory, and vehicle status.
- `I` / `Esc`: rest-house and week management; `1`–`5`: site-panel choices.
- `Space`: cast/reel at fishing spots.
- `B`: album picker; `V`: mute/unmute music.
- `F5`: save; `F9`: load.

Career mode loads `salmon_world_save.json`. If none exists, it imports the existing `salmon_farm_save.json` career, preserving its key farm progress and loaded cargo. New saves go to `salmon_world_save.json`; the legacy file is not overwritten.

## Focused checks

```powershell
Set-Location "C:\Users\jon-e\Documents\SalmonFarmerGame"
python verify_game.py
```

Three smoke checks cover the complete shift and its recovery cases (spill, interrupted pulling/pumping, wrong grading, rough driving), save isolation, and career farming/migration/movement. They also check the 100-point total, duplicate protection, feeding preview/impact agreement, cosmetic-only label flipping, and album startup/selection/shuffle/stop/mute/pause behavior. The five supplied MP3s are decoded through SDL; playback calls and transitions are checked with mocks. Video checks cover the 15-second music intro, the full clip from 0:00, soundtrack synchronization, pause/focus handling, missing files, and cleanup. They use temporary saves and SDL's dummy display, and render representative screens to ignored `verification-output/`. These checks do not verify audible playback or measure a first-time human playthrough; the 4–6 minute pacing target still needs that playtest.
