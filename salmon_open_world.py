import json
import math
import random
from pathlib import Path

import pygame

from salmon_shift import SalmonShiftMixin


LOGICAL_SIZE = (640, 400)
VIEW_HEIGHT = 336
WORLD_SIZE = (4096, 3072)
TILE_SIZE = 32

LANDMARKS = {
    "farm": {"name": "Tide & Tackle Farm", "pos": (1984, 1472), "color": (198, 151, 92), "size": (76, 58), "kind": "farm"},
    "pens": {"name": "SALMON FARM · NET PENS A-D", "pos": (2576, 1192), "color": (72, 155, 146), "size": (168, 120), "kind": "pens"},
    "hatchery": {"name": "Smolt Hatchery", "pos": (2370, 1010), "color": (116, 166, 160), "size": (112, 78), "kind": "hatchery"},
    "town": {"name": "Herring Cove", "pos": (1504, 1808), "color": (196, 119, 83), "size": (90, 68), "kind": "town"},
    "harbor": {"name": "Coldwater Harbor", "pos": (3176, 1840), "color": (207, 160, 86), "size": (86, 54), "kind": "harbor"},
    "mill": {"name": "Feed Mill", "pos": (1152, 1120), "color": (179, 135, 78), "size": (76, 58), "kind": "mill"},
    "workshop": {"name": "Truck Workshop", "pos": (2208, 2296), "color": (118, 133, 121), "size": (82, 60), "kind": "workshop"},
    "forest": {"name": "Pinewood Trail", "pos": (848, 2264), "color": (66, 119, 78), "size": (80, 52), "kind": "forest"},
    "lighthouse": {"name": "Stormglass Point", "pos": (3408, 800), "color": (214, 214, 185), "size": (34, 80), "kind": "lighthouse"},
    "visitor": {"name": "Coastal Research Station", "pos": (1632, 912), "color": (143, 171, 151), "size": (72, 54), "kind": "visitor"},
    "market": {"name": "Fish Market", "pos": (3296, 1856), "color": (201, 115, 79), "size": (88, 58), "kind": "market"},
    "pier": {"name": "Old Pier", "pos": (3008, 2032), "color": (142, 102, 69), "size": (54, 30), "kind": "pier"},
    "truck": {"name": "Farm Truck", "pos": (1984, 1648), "color": (189, 79, 59), "size": (50, 34), "kind": "truck"},
    "rest": {"name": "Coastal Rest House", "pos": (1648, 992), "color": (197, 178, 132), "size": (72, 48), "kind": "rest"},
}

ROAD_NETWORK = (
    ((1984, 1560), (2180, 1544), (2350, 1400), (2512, 1250), (2576, 1230)),
    ((1984, 1560), (1808, 1680), (1640, 1792), (1504, 1830)),
    ((1504, 1800), (1350, 1680), (1260, 1450), (1152, 1150)),
    ((1984, 1560), (2048, 1776), (2130, 2016), (2208, 2320)),
    ((2576, 1230), (2800, 1320), (2992, 1540), (3176, 1810)),
    ((3176, 1810), (3250, 1830), (3296, 1850)),
    ((1504, 1830), (1290, 1940), (1060, 2112), (848, 2280)),
    ((2576, 1192), (2750, 1020), (3060, 880), (3408, 830)),
    ((1984, 1472), (1850, 1290), (1720, 1080), (1632, 930)),
    ((3296, 1850), (3210, 1940), (3008, 2040)),
    ((2576, 1192), (2490, 1110), (2370, 1010)),
)


class SalmonOpenWorld(SalmonShiftMixin):
    def __init__(self, save_path: Path | None = None, legacy_path: Path | None = None) -> None:
        pygame.init()
        pygame.display.set_caption("Tide & Tackle: North Atlantic")
        size = pygame.display.get_surface().get_size() if pygame.display.get_surface() else (1280, 800)
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.canvas = pygame.Surface(LOGICAL_SIZE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 12, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 10, bold=True)
        self.large_font = pygame.font.SysFont("consolas", 22, bold=True)
        self.world_width, self.world_height = WORLD_SIZE
        self.save_path = save_path if save_path is not None else Path(__file__).with_name("salmon_world_save.json")
        self.legacy_path = legacy_path if legacy_path is not None else Path(__file__).with_name("salmon_farm_save.json")

        self.week = 1
        self.cash = 200_008_000
        self.fish = 22_000
        self.feed = 8200.0
        self.average_weight = .32
        self.health = 91
        self.water = 84
        self.oxygen = 79
        self.lice = 9
        self.market_price = 8.4
        self.harvested_kg = 0.0
        self.total_sales = 0
        self.reputation = 12
        self.level = 1
        self.experience = 0
        self.crew_level = 0
        self.loan = 0
        self.upgrades = {"aeration": 0, "biofilter": 0, "truck": 0, "feed": 0}
        self.contract = {"company": "Harbor Co-op", "target": 2400.0, "delivered": 0.0, "reward": 8500}
        self.notes: list[str] = ["A new life on the coast. Explore the island and meet the people who keep it running."]
        self.inventory = {"shells": 0, "driftwood": 0, "bait": 3, "wild_fish": 0}
        self.achievements: set[str] = set()
        self.hatchery = {
            "stage": "empty", "count": 0, "weeks": 0, "quality": 92,
            "vaccinated": False, "graded": False, "feed_kg": 2000,
            "transferred_total": 0,
        }

        self.player_x, self.player_y = 1940.0, 1656.0
        self.player_facing = 0.0
        self.player_stamina = 100.0
        self.inside_hatchery = False
        self.hatchery_exit_x = self.player_x
        self.hatchery_exit_y = self.player_y
        self.interior_x = 320.0
        self.interior_y = 300.0
        self.in_truck = False
        self.truck_x, self.truck_y = 1984.0, 1648.0
        self.truck_heading = 0.0
        self.truck_speed = 0.0
        self.truck_damage = 0.0
        self.truck_fuel = 70.0
        self.truck_cargo_kg = 0.0
        self.truck_capacity = 5200.0
        self.steering_input = 0.0

        self.day_clock = 9.0
        self.weather = "Clear"
        self.active_panel: str | None = None
        self.panel_message = ""
        self.toast = ""
        self.toast_timer = 0.0
        self.show_map = False
        self.show_journal = False
        self.running = True
        self.fishing_state = "idle"
        self.fishing_timer = 0.0
        self.collected = self._make_collectibles()
        self.camera_x = 0.0
        self.camera_y = 0.0
        self._init_shift_ui()

    def _make_collectibles(self) -> list[dict[str, float | str | bool]]:
        rng = random.Random(7941)
        items = []
        for _ in range(90):
            x = rng.randint(420, 3650)
            y = rng.randint(360, 2680)
            if self._on_island(x, y):
                items.append({"x": x, "y": y, "kind": rng.choice(("shell", "driftwood", "bait")), "taken": False})
        return items

    @staticmethod
    def _on_island(x: float, y: float) -> bool:
        dx = (x - 2048) / 1900
        dy = (y - 1536) / 1320
        return dx * dx + dy * dy < .94

    def _load_saved_or_legacy(self) -> None:
        if self.mode != "career":
            return
        source = self.save_path
        if not source.exists():
            old_save = self.legacy_path
            if old_save.exists():
                source = old_save
        if not source.exists():
            return
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._notify("Save could not be read. Starting a fresh island career.")
            return
        if source == self.save_path and data.get("format") == 1:
            self._apply_state(data)
            self._notify("Island career loaded. Welcome back to the coast.")
            return
        self.cash = int(data.get("cash", self.cash))
        self.fish = int(data.get("fish", self.fish))
        self.feed = float(data.get("feed", self.feed))
        self.average_weight = float(data.get("average_weight", self.average_weight))
        self.health = int(data.get("health", self.health))
        self.water = int(data.get("water", self.water))
        self.oxygen = int(data.get("oxygen", self.oxygen))
        self.lice = int(data.get("lice", self.lice))
        self.week = int(data.get("week", self.week))
        self.reputation = int(data.get("reputation", self.reputation))
        self.level = int(data.get("level", self.level))
        self.experience = int(data.get("experience", self.experience))
        self.harvested_kg = float(data.get("harvested_kg", 0.0))
        self.total_sales = int(data.get("total_sales", 0))
        self.loan = int(data.get("loan_debt", 0))
        old_upgrades = data.get("upgrades", {})
        for key in self.upgrades:
            self.upgrades[key] = int(old_upgrades.get("feed_efficiency" if key == "feed" else key, 0))
        old_contract = data.get("contract")
        if isinstance(old_contract, dict):
            self.contract = {
                "company": old_contract.get("name", "Harbor Co-op"),
                "target": float(old_contract.get("target", 2400)),
                "delivered": float(old_contract.get("delivered", 0)),
                "reward": int(old_contract.get("reward", 8500)),
            }
        self.truck_cargo_kg = float(data.get("truck_cargo_kg", 0))
        self._notify("Your existing farm career was carried into the open-world island. Visit the truck to continue.")

    def _apply_state(self, data: dict) -> None:
        scalar_fields = ("week", "cash", "fish", "feed", "average_weight", "health", "water", "oxygen", "lice", "market_price", "harvested_kg", "total_sales", "reputation", "level", "experience", "crew_level", "loan", "player_x", "player_y", "player_facing", "player_stamina", "in_truck", "truck_x", "truck_y", "truck_heading", "truck_speed", "truck_damage", "truck_fuel", "truck_cargo_kg", "truck_capacity", "day_clock", "weather")
        for field in scalar_fields:
            if field in data:
                setattr(self, field, data[field])
        self.upgrades.update(data.get("upgrades", {}))
        self.contract.update(data.get("contract", {}))
        self.inventory.update(data.get("inventory", {}))
        self.hatchery.update(data.get("hatchery", {}))
        self.inside_hatchery = bool(data.get("inside_hatchery", False))
        self.hatchery_exit_x = float(data.get("hatchery_exit_x", self.hatchery_exit_x))
        self.hatchery_exit_y = float(data.get("hatchery_exit_y", self.hatchery_exit_y))
        self.interior_x = float(data.get("interior_x", self.interior_x))
        self.interior_y = float(data.get("interior_y", self.interior_y))
        self.notes = list(data.get("notes", self.notes))[-8:]
        self.achievements = set(data.get("achievements", []))
        self.collected = data.get("collected", self.collected)

    def save(self) -> None:
        if self.mode != "career":
            return
        state = {
            "format": 1, "week": self.week, "cash": self.cash, "fish": self.fish,
            "feed": self.feed, "average_weight": self.average_weight, "health": self.health,
            "water": self.water, "oxygen": self.oxygen, "lice": self.lice,
            "market_price": self.market_price, "harvested_kg": self.harvested_kg,
            "total_sales": self.total_sales, "reputation": self.reputation, "level": self.level,
            "experience": self.experience, "crew_level": self.crew_level, "loan": self.loan,
            "upgrades": self.upgrades, "contract": self.contract, "notes": self.notes,
            "inventory": self.inventory, "achievements": sorted(self.achievements),
            "hatchery": self.hatchery, "inside_hatchery": self.inside_hatchery,
            "hatchery_exit_x": self.hatchery_exit_x, "hatchery_exit_y": self.hatchery_exit_y,
            "interior_x": self.interior_x, "interior_y": self.interior_y,
            "player_x": self.player_x, "player_y": self.player_y, "player_facing": self.player_facing,
            "player_stamina": self.player_stamina, "truck_x": self.truck_x, "truck_y": self.truck_y,
            "in_truck": self.in_truck, "truck_heading": self.truck_heading, "truck_speed": self.truck_speed,
            "truck_damage": self.truck_damage, "truck_fuel": self.truck_fuel,
            "truck_cargo_kg": self.truck_cargo_kg, "truck_capacity": self.truck_capacity,
            "day_clock": self.day_clock, "weather": self.weather, "collected": self.collected,
        }
        try:
            self.save_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            self._notify("Career saved.")
        except OSError as error:
            self._notify(f"Save failed: {error}")

    def _notify(self, message: str) -> None:
        self.toast = message
        self.toast_timer = 4.0
        self.notes.insert(0, message)
        self.notes = self.notes[:8]

    def _xp(self, amount: int) -> None:
        self.experience += amount
        while self.experience >= self.level * 100:
            self.experience -= self.level * 100
            self.level += 1
            self.reputation = min(100, self.reputation + 2)
            self.cash += 5000 * self.level
            self._notify(f"Farm level {self.level}! Development grant received.")

    def _advance_week(self) -> None:
        self.week += 1
        ration = self.fish * self.average_weight * max(.012, .024 - self.upgrades["feed"] * .002 - self.crew_level * .0004)
        self.cash -= 2450 + self.loan * .001
        if self.feed >= ration:
            self.feed -= ration
            self.average_weight += .055
            self.health = min(100, self.health + 1)
        else:
            self.feed = 0
            self.health = max(0, self.health - 8)
            self._notify("Feed ran short. Restock at the feed mill.")
        self.water = max(0, self.water - random.randint(1, 4) + self.upgrades["biofilter"] * 2)
        self.oxygen = max(0, self.oxygen - random.randint(1, 4) + self.upgrades["aeration"] * 2)
        self.lice = min(100, self.lice + random.randint(1, 4))
        self.market_price = round(max(5.0, min(13.0, self.market_price + random.uniform(-.6, .8))), 2)
        event = random.choice(("calm", "storm", "surge", "bloom", "inspection", "calm"))
        if event == "storm":
            self.weather = "Storm"
            self.water = max(0, self.water - 9)
            self.oxygen = max(0, self.oxygen - 6)
            self._notify("A gale rolled through the pens. Check the net lines.")
        elif event == "surge":
            self.weather = "Market surge"
            self.market_price = min(13.0, self.market_price + 1.1)
            self._notify("Restaurant demand spiked. Fish prices are up this week.")
        elif event == "bloom":
            self.weather = "Algal bloom"
            self.water = max(0, self.water - max(3, 11 - self.upgrades["biofilter"] * 2))
            self.health = max(0, self.health - 3)
            self._notify("An algal bloom is drifting near the island. Biofilters reduce the damage.")
        elif event == "inspection":
            self.weather = "Inspection day"
            if self.health > 70 and self.water > 60 and self.lice < 35:
                self.cash += 10000
                self.reputation = min(100, self.reputation + 2)
                self._notify("Clean-site inspection passed. A sustainability grant was awarded.")
            else:
                self.reputation = max(0, self.reputation - 1)
                self._notify("Inspection flagged the pens. Reputation fell slightly.")
        else:
            self.weather = random.choice(("Clear", "Light rain", "Breezy"))
        stress = max(0, 42 - self.water) // 8 + max(0, 38 - self.oxygen) // 8 + max(0, self.lice - 58) // 9
        if stress:
            lost = min(self.fish, int(self.fish * stress * .009))
            self.fish -= lost
            self.health = max(0, self.health - stress * 2)
            if lost:
                self._notify(f"Pen stress caused a loss of {lost:,} fish.")
        if self.health <= 0 or self.fish <= 0:
            self.fish = 6000
            self.average_weight = .24
            self.health = 58
            self.water = max(45, self.water)
            self.oxygen = max(45, self.oxygen)
            self.cash -= 25000
            self.reputation = max(0, self.reputation - 8)
            self._notify("A recovery cohort arrived. You can rebuild; the career continues.")
        if self.cash < 0:
            loan = max(50000, int(-self.cash * 1.15))
            self.cash += loan
            self.loan += loan
            self._notify("Emergency credit keeps the operation open. Review the farm ledger.")
        if self.week % 12 == 1:
            grant = self.reputation * 1800
            self.cash += grant
            self.reputation = min(100, self.reputation + 1)
            self._notify(f"Year {(self.week - 1) // 12 + 1} begins. Sustainability grant: ${grant:,}.")
        self._advance_hatchery_batch()
        self.day_clock = 7.0
        self._xp(20)
        self.save()

    def _advance_hatchery_batch(self) -> None:
        batch = self.hatchery
        stage = str(batch["stage"])
        if stage not in ("eggs", "alevins", "fry"):
            return
        batch["weeks"] = int(batch["weeks"]) + 1
        if stage in ("alevins", "fry"):
            if int(batch["feed_kg"]) >= 250:
                batch["feed_kg"] = int(batch["feed_kg"]) - 250
            else:
                batch["quality"] = max(0, int(batch["quality"]) - 12)
                self._notify("Hatchery nursery feed ran short. Smolt survival is falling.")
        if self.water < 50 or self.oxygen < 50:
            batch["quality"] = max(0, int(batch["quality"]) - 8)
            self._notify("Poor farm water conditions affected hatchery intake quality.")
        survival = .995 if int(batch["quality"]) >= 60 else .94
        batch["count"] = max(0, int(int(batch["count"]) * survival))
        duration = {"eggs": 2, "alevins": 2, "fry": 3}[stage]
        if int(batch["weeks"]) < duration:
            return
        next_stage = {"eggs": "alevins", "alevins": "fry", "fry": "smolt_ready"}[stage]
        batch["stage"] = next_stage
        batch["weeks"] = 0
        batch["vaccinated"] = False
        batch["graded"] = False
        stage_names = {"alevins": "alevins", "fry": "fry", "smolt_ready": "transfer-ready smolts"}
        self._notify(f"Hatchery batch developed into {stage_names[next_stage]}: {batch['count']:,} fish remain.")

    def _draw_text(self, target: pygame.Surface, text: str, pos: tuple[int, int], color=(240, 236, 205), font=None, center=False) -> None:
        image = (font or self.font).render(str(text), False, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        target.blit(image, rect)

    def _world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return round(x - self.camera_x), round(y - self.camera_y)

    @staticmethod
    def _segment_distance(px: float, py: float, start: tuple[int, int], end: tuple[int, int]) -> float:
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = dx * dx + dy * dy
        if not length:
            return math.hypot(px - start[0], py - start[1])
        t = max(0.0, min(1.0, ((px - start[0]) * dx + (py - start[1]) * dy) / length))
        return math.hypot(px - (start[0] + t * dx), py - (start[1] + t * dy))

    def _road_distance(self, x: float, y: float) -> float:
        closest = 99999.0
        for road in ROAD_NETWORK:
            for start, end in zip(road, road[1:]):
                closest = min(closest, self._segment_distance(x, y, start, end))
        return closest

    def _draw_world(self) -> None:
        if self.inside_hatchery:
            self._draw_hatchery_interior()
            self._draw_interaction_hint()
            return
        screen = self.canvas
        screen.fill((30, 111, 132), (0, 0, LOGICAL_SIZE[0], VIEW_HEIGHT))
        island = pygame.Rect(round(148 - self.camera_x), round(216 - self.camera_y), 3800, 2640)
        pygame.draw.ellipse(screen, (42, 104, 112), island.inflate(30, 22))
        pygame.draw.ellipse(screen, (178, 174, 126), island.inflate(10, 8))
        pygame.draw.ellipse(screen, (111, 145, 87), island)

        first_x = max(0, int(self.camera_x // TILE_SIZE) - 1)
        last_x = min(self.world_width // TILE_SIZE, int((self.camera_x + LOGICAL_SIZE[0]) // TILE_SIZE) + 2)
        first_y = max(0, int(self.camera_y // TILE_SIZE) - 1)
        last_y = min(self.world_height // TILE_SIZE, int((self.camera_y + VIEW_HEIGHT) // TILE_SIZE) + 2)
        for tile_x in range(first_x, last_x):
            for tile_y in range(first_y, last_y):
                wx, wy = tile_x * TILE_SIZE, tile_y * TILE_SIZE
                if not self._on_island(wx + 16, wy + 16):
                    continue
                sx, sy = wx - self.camera_x, wy - self.camera_y
                seed = (tile_x * 73856093 ^ tile_y * 19349663) & 0xFFFFFFFF
                if seed % 13 == 0:
                    color = (116, 151, 90)
                    pygame.draw.rect(screen, color, (sx, sy, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(screen, (130, 158, 96), (sx + 5, sy + 5, 4, 3))
                elif seed % 47 == 0:
                    pygame.draw.rect(screen, (126, 144, 91), (sx + 11, sy + 9, 6, 5))
                    pygame.draw.rect(screen, (91, 119, 72), (sx + 14, sy + 11, 3, 3))
                if seed % 17 == 0:
                    pygame.draw.rect(screen, (153, 160, 101), (sx + 3, sy + 22, 2, 2))

        for road in ROAD_NETWORK:
            points = [self._world_to_screen(*point) for point in road]
            pygame.draw.lines(screen, (105, 91, 69), False, points, 20)
            pygame.draw.lines(screen, (196, 174, 125), False, points, 15)
            pygame.draw.lines(screen, (211, 193, 148), False, points, 2)

        self._draw_rocks_and_trees()
        for key, landmark in LANDMARKS.items():
            if key == "truck":
                continue
            self._draw_building(key, landmark)
        self._draw_coastal_details()
        self._draw_npcs()
        self._draw_truck()
        if not self.in_truck:
            self._draw_player()

        self._draw_interaction_hint()
        self._draw_day_tint()

    def _draw_rocks_and_trees(self) -> None:
        first_x = max(0, int(self.camera_x // 128) - 1)
        last_x = min(32, int((self.camera_x + 640) // 128) + 2)
        first_y = max(0, int(self.camera_y // 128) - 1)
        last_y = min(24, int((self.camera_y + VIEW_HEIGHT) // 128) + 2)
        for cell_x in range(first_x, last_x):
            for cell_y in range(first_y, last_y):
                seed = (cell_x * 83492791 ^ cell_y * 2654435761) & 0xFFFFFFFF
                rng = random.Random(seed)
                for _ in range(3):
                    wx = cell_x * 128 + rng.randint(8, 120)
                    wy = cell_y * 128 + rng.randint(8, 120)
                    if not self._on_island(wx, wy) or self._near_road(wx, wy, 44) or self._near_building(wx, wy, 80):
                        continue
                    sx, sy = self._world_to_screen(wx, wy)
                    if seed % 4:
                        pygame.draw.rect(self.canvas, (53, 93, 62), (sx - 5, sy - 7, 11, 10))
                        pygame.draw.rect(self.canvas, (69, 119, 70), (sx - 7, sy - 11, 14, 8))
                        pygame.draw.rect(self.canvas, (82, 134, 75), (sx - 4, sy - 15, 9, 7))
                        pygame.draw.rect(self.canvas, (99, 75, 52), (sx - 2, sy - 1, 4, 8))
                    else:
                        pygame.draw.rect(self.canvas, (103, 105, 87), (sx - 4, sy - 3, 9, 6))
                        pygame.draw.rect(self.canvas, (135, 130, 105), (sx - 2, sy - 5, 4, 3))

    def _near_road(self, x: float, y: float, threshold: float) -> bool:
        return self._road_distance(x, y) < threshold

    def _near_building(self, x: float, y: float, threshold: float) -> bool:
        return any(math.dist((x, y), data["pos"]) < threshold for data in LANDMARKS.values())

    def _draw_building(self, key: str, landmark: dict) -> None:
        x, y = self._world_to_screen(*landmark["pos"])
        width, height = landmark["size"]
        if x < -160 or x > 800 or y < -120 or y > 500:
            return
        if key == "pens":
            self._draw_salmon_pens(x, y)
            return
        if key == "hatchery":
            self._draw_hatchery_exterior(x, y)
            return
        width = max(18, width // 3)
        height = max(15, height // 3)
        body = pygame.Rect(x - width // 2, y - height // 2, width, height)
        pygame.draw.rect(self.canvas, (62, 64, 55), body.inflate(4, 3))
        pygame.draw.rect(self.canvas, landmark["color"], body)
        pygame.draw.rect(self.canvas, tuple(max(0, channel - 34) for channel in landmark["color"]), (body.x, body.y, body.w, 5))
        pygame.draw.rect(self.canvas, (234, 216, 164), (body.x + 4, body.y + 6, 5, 5))
        pygame.draw.rect(self.canvas, (234, 216, 164), (body.right - 9, body.y + 6, 5, 5))
        pygame.draw.rect(self.canvas, (84, 65, 46), (x - 3, body.bottom - 9, 6, 9))
        if key == "lighthouse":
            pygame.draw.rect(self.canvas, (236, 224, 189), (x - 5, y - 24, 10, 34))
            pygame.draw.rect(self.canvas, (190, 78, 62), (x - 6, y - 26, 12, 7))
            pygame.draw.rect(self.canvas, (239, 215, 134), (x - 4, y - 31, 8, 5))
        label = landmark["name"].upper()
        if self.mode == "shift" and key == "market":
            return  # The receiving platform has its own readable entrance sign.
        text = self.small_font.render(label, False, (247, 239, 200))
        tag = pygame.Rect(x - text.get_width() // 2 - 3, body.bottom + 2, text.get_width() + 6, 12)
        pygame.draw.rect(self.canvas, (44, 63, 56), tag)
        self.canvas.blit(text, (tag.x + 3, tag.y + 2))

    def _draw_salmon_pens(self, x: int, y: int) -> None:
        if self.mode == "shift":
            canvas = self.canvas
            tile = pygame.Surface((206, 161), pygame.SRCALPHA)
            self.canvas = tile
            try:
                self._paint_salmon_pens(103, 92)
            finally:
                self.canvas = canvas
            self.canvas.blit(pygame.transform.scale(tile, (296, 232)), (x - 148, y - 133))
        else:
            self._paint_salmon_pens(x, y)

    def _paint_salmon_pens(self, x: int, y: int) -> None:
        t = self._art_time()
        # A seawater basin with working perimeter decking, not four lawn ponds.
        pygame.draw.rect(self.canvas, (56, 81, 70), (x - 97, y - 65, 194, 133))
        pygame.draw.rect(self.canvas, (151, 109, 70), (x - 93, y - 62, 186, 124))
        for plank_x in range(x - 90, x + 93, 9):
            pygame.draw.line(self.canvas, (191, 151, 101), (plank_x, y - 61), (plank_x, y + 60))
        pygame.draw.rect(self.canvas, (34, 108, 124), (x - 77, y - 46, 154, 92))
        for row in range(8):
            for col in range(4):
                rx = x - 71 + col * 36 + int(math.sin(t + row) * 3)
                ry = y - 41 + row * 11
                pygame.draw.line(self.canvas, (48, 137, 145), (rx, ry), (rx + 12, ry), 1)
        # Crosswalk above the water. All collision/interaction positions stay put.
        pygame.draw.rect(self.canvas, (100, 74, 55), (x - 78, y - 5, 156, 10))
        for px in range(x - 77, x + 78, 8):
            pygame.draw.rect(self.canvas, (194, 151, 101), (px, y - 4, 6, 8))
        for px, py in ((x - 90, y - 58), (x + 90, y - 58), (x - 90, y + 58), (x + 90, y + 58)):
            pygame.draw.line(self.canvas, (212, 197, 143), (px, py), (x, y), 1)
            pygame.draw.rect(self.canvas, (79, 64, 52), (px - 2, py - 3, 5, 7))
        centers = ((x - 36, y - 23), (x + 36, y - 23), (x - 36, y + 23), (x + 36, y + 23))
        for index, (pen_x, pen_y) in enumerate(centers):
            pond = pygame.Rect(pen_x - 28, pen_y - 18, 56, 36)
            shake = round(math.sin(t * 34) * self.shift_hold) if self.mode == "shift" and self._task()[0] == "nets" else 0
            pond.move_ip(shake, 0)
            pygame.draw.ellipse(self.canvas, (25, 72, 88), pond.move(1, 4).inflate(5, 3))
            pygame.draw.ellipse(self.canvas, (218, 203, 148), pond.inflate(4, 4), 3)
            water_color = (40, 148, 147) if self.mode == "shift" and "Cleaned" in self.shift_care else (37, 132, 139)
            pygame.draw.ellipse(self.canvas, water_color, pond)
            pygame.draw.ellipse(self.canvas, (72, 171, 161), pond.inflate(-8, -7), 1)
            for fish_index in range(6):
                phase = t * .9 + fish_index * 1.7 + index
                fish_x = pen_x + math.sin(phase) * 15
                fish_y = pen_y + math.cos(phase * .7) * 8
                facing = 1 if math.cos(phase) > 0 else -1
                if self.mode == "shift" and (self.effect == "feed" and self.effect_seconds > 0 or self.scoop_ready or self.feed_spill):
                    # School toward the feeding side while remaining in each net.
                    source = self._task_target() if self.scoop_ready or self.feed_spill else self.shift_feed_point
                    target_x, target_y = x + (source[0] - 2576) / 1.44, y + (source[1] - 1192) / 1.44
                    fish_x = pen_x + max(-13, min(13, target_x - pen_x)) + math.sin(t * 5 + fish_index) * 5
                    fish_y = pen_y + max(-6, min(6, target_y - pen_y)) + math.cos(t * 5 + fish_index) * 4
                    facing = 1 if target_x >= pen_x else -1
                    if self.scoop_ready:
                        fish_x, fish_y = pen_x - 17 + fish_index * 6, pen_y
                length = 9 if self.mode == "shift" and index == 3 and self.shift_juveniles else 13
                pygame.draw.ellipse(self.canvas, (30, 113, 123), (fish_x - 6, fish_y + 2, 12, 4))
                self._draw_fish(self.canvas, fish_x, fish_y, length, t + fish_index, facing)
            splash = (t + index * 1.3) % 4
            if splash < .6:
                pygame.draw.ellipse(self.canvas, (173, 224, 206), (pen_x + 7, pen_y + 5, 5 + int(splash * 12), 3 + int(splash * 5)), 1)
            for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
                bx, by = pen_x + int(math.cos(angle) * 29), pen_y + int(math.sin(angle) * 19)
                pygame.draw.circle(self.canvas, (243, 188, 91), (bx, by), 2)
            label = f"PEN {chr(65 + index)}"
            if self.mode == "shift" and index == 2:
                label = "C MATURE"
            elif self.mode == "shift" and index == 3 and self.shift_juveniles:
                label = "D SMOLTS"
            width = max(34, self.small_font.size(label)[0] + 4)
            pygame.draw.rect(self.canvas, (35, 75, 77), (pen_x - width // 2, pen_y - 27, width, 10))
            self._draw_text(self.canvas, label, (pen_x, pen_y - 23), (255, 243, 203), self.small_font, center=True)
        shed = pygame.Rect(x - 12, y + 47, 24, 12)
        pygame.draw.rect(self.canvas, (57, 62, 52), shed.inflate(3, 2))
        pygame.draw.rect(self.canvas, (218, 205, 162), shed)
        pygame.draw.rect(self.canvas, (160, 83, 64), (shed.x - 2, shed.y - 3, shed.w + 4, 4))
        sign = self.font.render("SALMON FARM  ·  NET PENS A-D", False, (255, 243, 199))
        sign_rect = pygame.Rect(x - sign.get_width() // 2 - 7, y - 85, sign.get_width() + 14, 18)
        pygame.draw.rect(self.canvas, (34, 65, 57), sign_rect)
        pygame.draw.rect(self.canvas, (229, 197, 132), sign_rect, 1)
        self.canvas.blit(sign, (sign_rect.x + 7, sign_rect.y + 4))

    def _draw_hatchery_exterior(self, x: int, y: int) -> None:
        building = pygame.Rect(x - 42, y - 21, 84, 42)
        pygame.draw.rect(self.canvas, (54, 66, 59), building.inflate(6, 4))
        pygame.draw.rect(self.canvas, (189, 207, 184), building)
        pygame.draw.rect(self.canvas, (76, 126, 119), (building.x, building.y, building.w, 8))
        pygame.draw.polygon(self.canvas, (76, 126, 119), ((x - 49, y - 20), (x, y - 39), (x + 49, y - 20)))
        for tank_x in (x - 58, x + 58):
            pygame.draw.ellipse(self.canvas, (43, 76, 70), (tank_x - 17, y - 11, 34, 26))
            pygame.draw.ellipse(self.canvas, (54, 145, 147), (tank_x - 14, y - 9, 28, 21))
            pygame.draw.ellipse(self.canvas, (205, 226, 193), (tank_x - 14, y - 9, 28, 21), 2)
        pygame.draw.rect(self.canvas, (74, 91, 70), (x - 6, y + 8, 12, 13))
        for window_x in (x - 30, x + 19):
            pygame.draw.rect(self.canvas, (87, 161, 163), (window_x, y - 10, 11, 10))
            pygame.draw.rect(self.canvas, (232, 222, 185), (window_x, y - 10, 11, 10), 1)
        sign = self.font.render("SMOLT HATCHERY", False, (255, 244, 208))
        sign_rect = pygame.Rect(x - sign.get_width() // 2 - 5, y + 27, sign.get_width() + 10, 16)
        pygame.draw.rect(self.canvas, (36, 70, 62), sign_rect)
        self.canvas.blit(sign, (sign_rect.x + 5, sign_rect.y + 3))

    def _draw_hatchery_interior(self) -> None:
        self.canvas.fill((43, 91, 87), (0, 0, 640, VIEW_HEIGHT))
        pygame.draw.rect(self.canvas, (184, 194, 165), (18, 26, 604, 294))
        pygame.draw.rect(self.canvas, (56, 91, 83), (18, 26, 604, 36))
        pygame.draw.line(self.canvas, (225, 219, 181), (18, 62), (622, 62), 3)
        for tile_x in range(30, 620, 24):
            for tile_y in range(70, 316, 24):
                color = (175, 187, 159) if (tile_x // 24 + tile_y // 24) % 2 else (183, 193, 166)
                pygame.draw.rect(self.canvas, color, (tile_x, tile_y, 23, 23))
        self._draw_text(self.canvas, "FRESHWATER HATCHERY  ·  CLEAN ZONE", (320, 42), (247, 238, 200), self.font, center=True)

        # Egg room: stacked trays with visible eggs and a flow-control panel.
        pygame.draw.rect(self.canvas, (74, 83, 69), (69, 79, 102, 78))
        pygame.draw.rect(self.canvas, (130, 143, 113), (73, 83, 94, 70))
        for shelf_y in (91, 111, 131):
            pygame.draw.rect(self.canvas, (75, 106, 97), (81, shelf_y, 76, 12))
            for egg_x in range(87, 153, 9):
                if self.mode != "shift" or self.hatchery["stage"] == "eggs":
                    pygame.draw.circle(self.canvas, (238, 162, 87), (egg_x, shelf_y + 5), 2)
                    pygame.draw.rect(self.canvas, (255, 207, 124), (egg_x, shelf_y + 4, 1, 1))
        pygame.draw.rect(self.canvas, (69, 105, 96), (91, 161, 56, 10))
        self._draw_text(self.canvas, "INCUBATORS", (120, 176), (43, 61, 53), self.small_font, center=True)

        # Nursery tanks and their independent feed and oxygen lines.
        for tank_x, tank_y in ((257, 104), (317, 104), (257, 151), (317, 151)):
            tank = pygame.Rect(tank_x - 23, tank_y - 17, 46, 34)
            pygame.draw.ellipse(self.canvas, (53, 83, 75), tank.inflate(4, 4))
            pygame.draw.ellipse(self.canvas, (49, 142, 146), tank)
            pygame.draw.ellipse(self.canvas, (205, 226, 189), tank, 2)
            if self.mode != "shift" or self.hatchery["stage"] in ("alevins", "fry", "smolt_ready"):
                for fish_index in range(3):
                    phase = self._art_time() * 1.5 + fish_index * 2
                    meeting = self.mode == "shift" and self.effect == "nursery" and self.effect_seconds > 0
                    fx = tank_x + (fish_index - 1) * 11 if meeting else tank_x + math.sin(phase) * 12
                    fy = tank_y if meeting else tank_y + math.cos(phase) * 6
                    self._draw_fish(self.canvas, fx, fy, 11, phase)
            bubble = self._art_time() * 8 % 20
            pygame.draw.circle(self.canvas, (177, 225, 211), (tank_x + 14, round(tank_y + 10 - bubble)), 2, 1)
        pygame.draw.rect(self.canvas, (206, 189, 139), (278, 77, 18, 8))
        self._draw_text(self.canvas, "ALEVIN / FRY NURSERY", (288, 184), (43, 61, 53), self.small_font, center=True)

        # Health lab with sample bench, microscope, and vaccine cooler.
        pygame.draw.rect(self.canvas, (76, 102, 90), (419, 83, 151, 72))
        pygame.draw.rect(self.canvas, (218, 219, 187), (427, 125, 135, 20))
        pygame.draw.rect(self.canvas, (142, 166, 143), (446, 104, 11, 21))
        pygame.draw.rect(self.canvas, (195, 210, 180), (450, 97, 23, 6))
        pygame.draw.line(self.canvas, (222, 228, 193), (464, 102), (464, 121), 3)
        pygame.draw.rect(self.canvas, (98, 161, 158), (506, 94, 37, 28))
        pygame.draw.rect(self.canvas, (225, 231, 200), (510, 99, 29, 4))
        self._draw_text(self.canvas, "HEALTH LAB  ·  VACCINES", (494, 169), (43, 61, 53), self.small_font, center=True)

        # Grading flume and the door to the seawater transfer dock.
        pygame.draw.rect(self.canvas, (82, 111, 95), (400, 221, 170, 38))
        pygame.draw.rect(self.canvas, (80, 159, 157), (406, 226, 158, 27))
        pygame.draw.line(self.canvas, (221, 219, 181), (406, 237), (564, 237), 3)
        pygame.draw.rect(self.canvas, (132, 101, 67), (295, 282, 50, 38))
        pygame.draw.rect(self.canvas, (218, 205, 166), (305, 282, 30, 38))
        self._draw_text(self.canvas, "GRADING FLUME", (485, 271), (43, 61, 53), self.small_font, center=True)
        # Color-coded stations, supply pipes and sacks are visual only.
        for color, rect in (((224, 160, 79), (73, 81, 94, 3)), ((79, 163, 164), (232, 78, 109, 3)),
                            ((173, 115, 122), (419, 81, 151, 3)), ((94, 151, 115), (400, 219, 170, 3))):
            pygame.draw.rect(self.canvas, color, rect)
        pygame.draw.lines(self.canvas, (79, 118, 111), False, [(183, 86), (205, 86), (205, 144), (231, 144)], 5)
        pygame.draw.lines(self.canvas, (144, 185, 163), False, [(183, 85), (205, 85), (205, 143), (231, 143)], 2)
        for sack_x in (219, 237):
            pygame.draw.rect(self.canvas, (190, 162, 104), (sack_x, 209, 14, 22), border_radius=3)
            pygame.draw.line(self.canvas, (124, 111, 77), (sack_x + 2, 213), (sack_x + 12, 213))
            self._draw_text(self.canvas, "F", (sack_x + 4, 219), (82, 107, 83), self.small_font)
        self._draw_text(self.canvas, "LOADING BAY / EXIT", (320, 327), (246, 233, 195), self.small_font, center=True)

        player_x, player_y = round(self.interior_x), round(self.interior_y)
        pygame.draw.ellipse(self.canvas, (65, 77, 58), (player_x - 6, player_y + 5, 13, 5))
        pygame.draw.rect(self.canvas, (42, 91, 79), (player_x - 6, player_y - 8, 12, 13))
        pygame.draw.rect(self.canvas, (234, 189, 145), (player_x - 3, player_y - 14, 7, 7))
        if self.mode == "shift":
            self._draw_work_pose(player_x, player_y)
        self._draw_text(self.canvas, "WASD WALK  ·  E WORK STATION / EXIT", (12, 8), (251, 240, 202), self.small_font)

    def _draw_npcs(self) -> None:
        npcs = (("MARA", 1944, 1450, (229, 164, 102)), ("EIRIK", 1470, 1764, (201, 126, 104)), ("JUN", 3180, 1792, (220, 202, 134)), ("SVEIN", 2224, 2260, (168, 174, 151)), ("LIV", 1640, 876, (169, 197, 165)), ("OLD INA", 3360, 850, (193, 158, 117)))
        for name, wx, wy, color in npcs:
            x, y = self._world_to_screen(wx, wy)
            if not (-12 <= x <= 652 and -12 <= y <= VIEW_HEIGHT + 12):
                continue
            pygame.draw.rect(self.canvas, (64, 54, 45), (x - 4, y - 7, 9, 15))
            pygame.draw.rect(self.canvas, color, (x - 5, y - 7, 10, 8))
            pygame.draw.rect(self.canvas, (231, 189, 143), (x - 3, y - 12, 7, 6))
            if math.dist((wx, wy), (self.truck_x if self.in_truck else self.player_x, self.truck_y if self.in_truck else self.player_y)) < 100:
                self._draw_text(self.canvas, name, (x, y - 19), (255, 245, 195), self.small_font, center=True)

    def _draw_player(self) -> None:
        x, y = self._world_to_screen(self.player_x, self.player_y)
        pygame.draw.ellipse(self.canvas, (63, 76, 56), (x - 6, y + 5, 13, 5))
        pygame.draw.rect(self.canvas, (55, 68, 57), (x - 4, y - 2, 9, 10))
        pygame.draw.rect(self.canvas, (46, 101, 87), (x - 6, y - 8, 12, 9))
        pygame.draw.rect(self.canvas, (235, 189, 145), (x - 3, y - 13, 7, 6))
        pygame.draw.rect(self.canvas, (104, 74, 54), (x - 4, y - 14, 8, 3))
        direction = pygame.Vector2(math.sin(self.player_facing), -math.cos(self.player_facing))
        pygame.draw.line(self.canvas, (241, 226, 177), (x, y - 3), (x + int(direction.x * 10), y - 3 + int(direction.y * 10)), 2)
        if self.mode == "shift":
            self._draw_work_pose(x, y)

    def _truck_sprite(self) -> pygame.Surface:
        sprite = pygame.Surface((22, 34), pygame.SRCALPHA)
        pygame.draw.rect(sprite, (39, 46, 43), (1, 4, 4, 25))
        pygame.draw.rect(sprite, (39, 46, 43), (17, 4, 4, 25))
        pygame.draw.rect(sprite, (189, 79, 59), (4, 7, 14, 24))
        pygame.draw.rect(sprite, (216, 143, 76), (4, 20, 14, 10))
        pygame.draw.rect(sprite, (233, 224, 187), (5, 5, 12, 10))
        pygame.draw.rect(sprite, (120, 169, 163), (7, 6, 8, 6))
        pygame.draw.rect(sprite, (244, 213, 130), (5, 2, 3, 3))
        pygame.draw.rect(sprite, (244, 213, 130), (14, 2, 3, 3))
        if abs(self.truck_speed) > 3:
            tread = int(self._art_time() * abs(self.truck_speed) / 12) % 5
            for wheel_x in (1, 18):
                pygame.draw.line(sprite, (126, 143, 132), (wheel_x, 7 + tread), (wheel_x + 2, 7 + tread))
                pygame.draw.line(sprite, (126, 143, 132), (wheel_x, 23 + tread), (wheel_x + 2, 23 + tread))
        if self.truck_cargo_kg > 0:
            crate_rows = (17, 22, 27)[:self.loaded_crates] if self.mode == "shift" else (19, 25)
            for crate_y in crate_rows:
                pygame.draw.rect(sprite, (199, 163, 103), (6, crate_y, 10, 5))
                pygame.draw.line(sprite, (112, 91, 68), (10, crate_y), (10, crate_y + 4))
        if self.mode == "shift":
            braking = pygame.K_s in self.held_keys or pygame.K_DOWN in self.held_keys
        else:
            braking = pygame.key.get_pressed()[pygame.K_s] or pygame.key.get_pressed()[pygame.K_DOWN]
        for lamp_x in (5, 14):
            pygame.draw.rect(sprite, (255, 103, 75) if braking else (140, 69, 61), (lamp_x, 30, 3, 2))
        return sprite

    def _draw_truck(self) -> None:
        if self.mode == "shift" and self.shift_juveniles == 0:
            return
        sprite = self._truck_sprite()
        lean = 0
        if self.mode == "shift" and abs(self.truck_speed) > 8:
            lean = (int(pygame.K_d in self.held_keys) - int(pygame.K_a in self.held_keys)) * min(3, abs(self.truck_speed) / 40)
        rotated = pygame.transform.rotate(sprite, -math.degrees(self.truck_heading) + lean)
        x, y = self._world_to_screen(self.truck_x, self.truck_y)
        if self.mode == "shift" and self.crate_bounce > 0:
            y += round(math.sin((.6 - self.crate_bounce) / .6 * math.pi) * 3)
        if self.mode == "shift" and self.truck_arrival > 0:
            x += int(self.truck_arrival * 24)
            y += int(self.truck_arrival * 12)
        if abs(self.truck_speed) > 3:
            direction = pygame.Vector2(math.sin(self.truck_heading), -math.cos(self.truck_heading))
            for i in range(3):
                age = (self._art_time() * 2 + i / 3) % 1
                px, py = pygame.Vector2(x, y) - direction * (18 + age * 22)
                pygame.draw.circle(self.canvas, (151, 161, 137), (round(px), round(py)), 1 + int(age * 3), 1)
        self.canvas.blit(rotated, rotated.get_rect(center=(x, y)))
        if self.truck_cargo_kg > 0:
            pygame.draw.rect(self.canvas, (242, 232, 186), (x - 8, y + 12, 16, 3))
        if self.mode != "shift" and not self.in_truck and math.dist((self.player_x, self.player_y), (self.truck_x, self.truck_y)) < 140:
            self._draw_text(self.canvas, "FARM TRUCK", (x, y - 23), (255, 240, 197), self.small_font, center=True)

    def _draw_interaction_hint(self) -> None:
        if self.mode == "shift":
            return
        if self.inside_hatchery:
            station = self._nearest_hatchery_station()
            if station and station[1] < 54:
                message = f"E  WORK {station[0].replace('_', ' ').upper()} STATION"
            elif math.dist((self.interior_x, self.interior_y), (320, 302)) < 54:
                message = "E  EXIT TO ISLAND"
            else:
                message = "WASD WALK  ·  VISIT INCUBATOR / NURSERY / LAB / GRADER"
        elif self.in_truck:
            if self.truck_cargo_kg:
                market_x, market_y = LANDMARKS["market"]["pos"]
                delta_x, delta_y = market_x - self.truck_x, market_y - self.truck_y
                bearing = math.degrees(math.atan2(delta_x, -delta_y)) % 360
                compass = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")[round(bearing / 45) % 8]
                distance = math.dist((self.truck_x, self.truck_y), (market_x, market_y))
                message = f"DELIVERY  ·  MARKET {distance:.0f} M {compass}  ·  E UNLOAD WHEN PARKED"
            else:
                message = "E  PARK AND STEP OUT" if abs(self.truck_speed) < 14 else "SLOW DOWN TO PARK"
        else:
            nearest = self._nearest_landmark()
            nearest_item = self._nearest_collectible()
            if nearest_item:
                message = "E  PICK UP BEACH FIND"
            elif nearest and nearest[1] < 94:
                message = f"E  {LANDMARKS[nearest[0]]['name'].upper()}"
            else:
                message = "WASD MOVE  ·  SHIFT RUN  ·  E INTERACT  ·  M MAP  ·  J JOURNAL  ·  I FARM BOOK"
        self._draw_text(self.canvas, message, (12, 322), (255, 244, 205))

    def _draw_day_tint(self) -> None:
        if self.day_clock < 6 or self.day_clock > 19:
            shade = pygame.Surface((640, VIEW_HEIGHT), pygame.SRCALPHA)
            shade.fill((20, 32, 56, 92))
            self.canvas.blit(shade, (0, 0))
            for x, y in ((35, 28), (154, 47), (296, 19), (458, 57), (586, 32)):
                pygame.draw.rect(self.canvas, (248, 239, 189), (x, y, 2, 2))

    def _nearest_landmark(self) -> tuple[str, float] | None:
        x, y = (self.truck_x, self.truck_y) if self.in_truck else (self.player_x, self.player_y)
        options = [(key, math.dist((x, y), item["pos"])) for key, item in LANDMARKS.items()]
        return min(options, key=lambda item: item[1]) if options else None

    def _nearest_collectible(self) -> dict | None:
        candidates = [item for item in self.collected if not item["taken"] and math.dist((self.player_x, self.player_y), (item["x"], item["y"])) < 30]
        return candidates[0] if candidates else None

    def _draw_full_map(self) -> None:
        veil = pygame.Surface((640, VIEW_HEIGHT), pygame.SRCALPHA)
        veil.fill((20, 35, 34, 205))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(76, 36, 488, 256)
        pygame.draw.ellipse(self.canvas, (46, 112, 118), rect.inflate(8, 8))
        pygame.draw.ellipse(self.canvas, (111, 145, 87), rect)
        for road in ROAD_NETWORK:
            points = [(76 + x / self.world_width * rect.w, 36 + y / self.world_height * rect.h) for x, y in road]
            pygame.draw.lines(self.canvas, (207, 185, 131), False, points, 2)
        for key, landmark in LANDMARKS.items():
            x = 76 + landmark["pos"][0] / self.world_width * rect.w
            y = 36 + landmark["pos"][1] / self.world_height * rect.h
            pygame.draw.rect(self.canvas, (247, 205, 115), (int(x - 2), int(y - 2), 5, 5))
            if key in ("town", "harbor", "pens", "hatchery", "farm", "market"):
                self._draw_text(self.canvas, key.upper(), (int(x + 4), int(y - 4)), (255, 240, 197), self.small_font)
        x, y = (self.truck_x, self.truck_y) if self.in_truck else (self.player_x, self.player_y)
        marker = (76 + x / self.world_width * rect.w, 36 + y / self.world_height * rect.h)
        pygame.draw.circle(self.canvas, (255, 95, 73), (round(marker[0]), round(marker[1])), 4)
        self._draw_text(self.canvas, "NORTH ATLANTIC ISLAND  ·  M TO CLOSE", (320, 15), (255, 243, 205), self.font, center=True)

    def _draw_journal(self) -> None:
        hatchery_line = f"HATCHERY  {str(self.hatchery['stage']).replace('_', ' ').upper()}  ·  {int(self.hatchery['count']):,} SMOLTS  ·  {int(self.hatchery['quality'])}% QUALITY"
        self._draw_overlay_box("FIELD JOURNAL", [
            f"WEEK {(self.week - 1) % 12 + 1:02d}  YEAR {(self.week - 1) // 12 + 1:02d}  ·  {self.weather.upper()}",
            hatchery_line,
            f"CONTRACT  {self.contract['company']}  ·  {self.contract['delivered']:.0f}/{self.contract['target']:.0f} KG",
            f"REWARD  ${self.contract['reward']:,}    REPUTATION  {self.reputation}    LEVEL  {self.level}",
            f"TRUCK  {self.truck_damage:.0f}% DAMAGE  ·  {self.truck_fuel:.0f} L FUEL  ·  {self.truck_cargo_kg:.0f} KG CARGO",
            f"PACK  {self.inventory['wild_fish']} WILD FISH  ·  {self.inventory['shells']} SHELLS  ·  {self.inventory['driftwood']} DRIFTWOOD  ·  {self.inventory['bait']} BAIT",
            f"HATCHERY FEED  {int(self.hatchery['feed_kg']):,} KG  ·  TRANSFERRED  {int(self.hatchery['transferred_total']):,}",
            f"FIELD NOTE  {self.notes[0][:62] if self.notes else 'No recent activity'}",
            "J OR ESC TO CLOSE",
        ])

    def _draw_panel(self) -> None:
        panel_data = self._panel_content()
        self._draw_overlay_box(panel_data[0], panel_data[1])

    def _draw_overlay_box(self, title: str, lines: list[str]) -> None:
        box = pygame.Rect(86, 55, 468, 230)
        pygame.draw.rect(self.canvas, (29, 43, 41), box.inflate(8, 8))
        pygame.draw.rect(self.canvas, (215, 192, 139), box, 2)
        pygame.draw.rect(self.canvas, (44, 64, 56), (box.x + 2, box.y + 2, box.w - 4, 30))
        title_font = self.large_font if self.large_font.size(title)[0] <= box.w - 24 else self.font
        self._draw_text(self.canvas, title, (box.x + 12, box.y + 9), (249, 226, 163), title_font)
        for index, line in enumerate(lines[:9]):
            self._draw_text(self.canvas, line, (box.x + 14, box.y + 44 + index * 17), (237, 236, 211), self.small_font if len(line) > 54 else self.font)

    def _panel_content(self) -> tuple[str, list[str]]:
        batch = self.hatchery
        batch_status = f"{str(batch['stage']).replace('_', ' ').upper()}  ·  {int(batch['count']):,} FISH  ·  QUALITY {int(batch['quality'])}%"
        if self.active_panel == "incubator":
            return "EGG INCUBATION ROOM  ·  SELECT 1-3", [
                batch_status,
                f"WEEK IN STAGE {batch['weeks']}  ·  FARM WATER {self.water}%  ·  OXYGEN {self.oxygen}%",
                "1  RECEIVE 10,000 FERTILIZED EGGS  ·  $2,500",
                "2  TEST INTAKE WATER  ·  SET BATCH QUALITY FROM FARM CONDITIONS",
                "3  CALIBRATE FLOW PUMP  ·  $1,000, QUALITY +8",
                "Eggs need two farm weeks here before they hatch.",
                "Walk to the nursery tanks to care for alevins and fry.",
                "", "E OR ESC CLOSES THIS STATION",
            ]
        if self.active_panel == "nursery":
            return "ALEVIN & FRY NURSERY  ·  SELECT 1-2", [
                batch_status,
                f"STARTER FEED  {int(batch['feed_kg']):,} KG  ·  WEEK IN STAGE {batch['weeks']}",
                "1  FEED AND CLEAN TANKS  ·  USE 250 KG, QUALITY +8",
                "2  ORDER 1,500 KG STARTER FEED  ·  $1,200",
                "Alevins and fry need nursery feed each farm week.",
                "Alevins need two weeks; fry need three before grading.",
                "", "E OR ESC CLOSES THIS STATION",
            ]
        if self.active_panel == "hatchery_lab":
            return "FISH HEALTH & VACCINE LAB  ·  SELECT 1-2", [
                batch_status,
                f"VACCINE STATUS  {'COMPLETE' if batch['vaccinated'] else 'NOT VACCINATED'}",
                "1  VACCINATE READY SMOLTS  ·  $0.20 PER FISH",
                "2  HEALTH SCREEN THE BATCH  ·  $500, QUALITY +5",
                "Vaccination is required before fish can leave freshwater.",
                "", "E OR ESC CLOSES THIS STATION",
            ]
        if self.active_panel == "grader":
            return "SMOLT GRADING & TRANSFER FLUME  ·  SELECT 1-2", [
                batch_status,
                f"VACCINATED  {batch['vaccinated']}  ·  GRADED  {batch['graded']}",
                "1  GRADE READY SMOLTS  ·  REMOVE UNSUITABLE FISH",
                "2  TRANSFER GRADED SMOLTS TO OPEN-WATER PENS  ·  $1,200",
                "Only vaccinated, graded, transfer-ready smolts can be stocked.",
                "", "E OR ESC CLOSES THIS STATION",
            ]
        if self.active_panel == "pens":
            return "SALMON PENS  ·  SELECT 1-5", [
                f"STOCK {self.fish:,}  ·  AVG {self.average_weight:.2f} KG  ·  HEALTH {self.health}%",
                f"WATER {self.water}%  ·  OXYGEN {self.oxygen}%  ·  LICE PRESSURE {self.lice}%",
                "1  FEED THE PENS  ·  750 KG FEED, HEALTH +5",
                "2  SERVICE NETS  ·  $1,200, WATER +18",
                "3  TREAT LICE  ·  $1,600, PRESSURE -28",
                f"4  HATCHERY BATCH  ·  {int(self.hatchery['count']):,} {str(self.hatchery['stage']).upper()}",
                "5  LOAD DELIVERY TRUCK  ·  UP TO 5,200 KG",
                "", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "farm":
            return "FARM OFFICE  ·  SELECT 1-5", [
                f"CASH ${self.cash:,.0f}  ·  CREDIT ${self.loan:,.0f}  ·  CREW LEVEL {self.crew_level}",
                "1  AERATION NETWORK  ·  $18,000 PER LEVEL",
                "2  BIOFILTERS  ·  $24,000 PER LEVEL",
                "3  TRUCK REFRIGERATION  ·  $16,000 PER LEVEL",
                "4  FEED RESEARCH  ·  $20,000 PER LEVEL",
                "5  TRAIN CREW  ·  $9,000 PER LEVEL",
                "", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "town":
            return "HERRING COVE  ·  TOWN BOARD", [
                f"CURRENT CUSTOMER: {self.contract['company']}",
                f"DELIVER {self.contract['target']:.0f} KG  ·  PAID ${self.contract['reward']:,}",
                "Meet the co-op manager for new work and weekly market news.",
                "Visit the fish market after loading your truck at the pens.",
                "", "1  ASK ABOUT THE ISLAND JOBS", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "market":
            return "COLDWATER FISH MARKET", [
                f"MARKET PRICE  ${self.market_price:.2f}/KG  ·  REPUTATION PREMIUM {self.reputation / 10:.1f}%",
                f"TRUCK CARGO  {self.truck_cargo_kg:,.0f} KG",
                "Park the loaded truck in the marked yard, then press E.",
                "Deliveries progress customer contracts and build your carrier streak.",
                "", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "mill":
            return "NORTH SHORE FEED MILL", [
                f"STORE  {self.feed:,.0f} KG  ·  WEEKLY RATION {self.fish * self.average_weight * .024:,.0f} KG",
                "1  ORDER 2,000 KG FEED  ·  $2,400",
                "2  ORDER 10,000 KG FEED  ·  $10,800",
                "3  BUY 5 BAIT  ·  $400",
                "", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "workshop":
            return "ISLAND MOTOR WORKS", [
                f"TRUCK CONDITION {self.truck_damage:.0f}% DAMAGE  ·  {self.truck_fuel:.0f} L",
                f"UPGRADES {self.upgrades['truck']}/5  ·  CAPACITY {self.truck_capacity:,.0f} KG",
                "1  REPAIR THE TRUCK  ·  COSTS $95 PER DAMAGE POINT",
                "2  FULL SERVICE  ·  $4,000, RESTORE FUEL AND CONDITION",
                "3  ENGINE AND TANK UPGRADE  ·  $16,000",
                "", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "forest":
            return "PINEWOOD TRAIL", [
                "A quiet trail loops above the cove. The locals leave useful things here.",
                f"YOUR PACK: {self.inventory['driftwood']} DRIFTWOOD  ·  {self.inventory['shells']} SHELLS",
                "1  TRAIL CLEAN-UP  ·  EXCHANGE 5 DRIFTWOOD FOR $900",
                "2  LISTEN FOR THE COASTAL BIRD COUNT  ·  EARN REPUTATION",
                "", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "lighthouse":
            prompt = "Press SPACE to cast." if self.fishing_state == "idle" else "Wait for the float to dip, then press SPACE!" if self.fishing_state == "waiting" else "NOW! PRESS SPACE TO REEL!" if self.fishing_state == "bite" else "Catch landed. Press SPACE for another cast."
            return "STORMGLASS POINT  ·  COAST FISHING", [
                "A small break from the farm. A bite is brief, so watch the float.",
                f"BAIT {self.inventory['bait']}  ·  SHELLS {self.inventory['shells']}  ·  {prompt}",
                "SPACE CAST / REEL   ·   ESC LEAVE THE SHORE",
            ]
        if self.active_panel == "visitor":
            return "COASTAL RESEARCH STATION", [
                "The researchers monitor wild salmon, water quality, and migration.",
                "1  SHARE YOUR WEEKLY WATER SAMPLE  ·  REPUTATION +2",
                "2  READ THE FIELD BOARD  ·  REVIEW FARM STATUS",
                "", "E OR ESC TO CLOSE",
            ]
        if self.active_panel == "pier":
            return "OLD PIER", [
                "The ferry runs to a small outer skerry. The ticket booth is closed today.",
                "Collect driftwood and shells along the high-tide line.",
                "A good place to cast when the weather is calm.",
                "", "E OR ESC TO CLOSE",
            ]
        return "COASTAL REST HOUSE", [
            f"Current time {int(self.day_clock):02d}:00  ·  {self.weather.upper()}",
            "1  REST UNTIL MORNING  ·  RECOVER STAMINA, ADVANCE THE FARM WEEK",
            "2  SAVE CAREER",
            "", "E OR ESC TO CLOSE",
        ]

    def _draw_hud(self) -> None:
        pygame.draw.rect(self.canvas, (28, 45, 44), (0, VIEW_HEIGHT, 640, 64))
        pygame.draw.rect(self.canvas, (190, 165, 117), (0, VIEW_HEIGHT, 640, 2))
        year = (self.week - 1) // 12 + 1
        week = (self.week - 1) % 12 + 1
        season = ("SPRING", "SUMMER", "AUTUMN", "WINTER")[(week - 1) // 3]
        self._draw_text(self.canvas, f"WEEK {week:02d}  YEAR {year:02d}  {season}  {int(self.day_clock):02d}:00", (10, 342), (242, 220, 168))
        self._draw_text(self.canvas, f"${self.cash:,.0f}  ·  {self.fish:,} FISH  ·  {self.feed:,.0f} KG FEED", (10, 359), (241, 239, 213))
        self._draw_text(self.canvas, f"CONTRACT: {self.contract['company']}  {self.contract['delivered']:.0f}/{self.contract['target']:.0f} KG", (10, 373), (217, 225, 191), self.small_font)
        if self.in_truck:
            speed = abs(self.truck_speed)
            self._draw_text(self.canvas, f"{speed * .36:.0f} KM/H  ·  {self.truck_fuel:.0f} L  ·  DAMAGE {self.truck_damage:.0f}%  ·  {self.truck_cargo_kg:.0f} KG", (330, 342), (249, 209, 135))
            self._draw_text(self.canvas, "W GAS  S BRAKE/REVERSE  A/D TURN  ·  E PARK", (330, 359), (207, 218, 197))
        else:
            self._draw_text(self.canvas, f"HEALTH {self.health}%  ·  WATER {self.water}%  ·  LICE {self.lice}%", (355, 342), (207, 218, 197))
            self._draw_text(self.canvas, f"LV {self.level}  ·  {self.experience}/{self.level * 100} XP  ·  REP {self.reputation}", (355, 359), (207, 218, 197))
        if self.toast_timer > 0:
            toast = self.font.render(self.toast[:80], False, (255, 239, 187))
            bg = pygame.Rect(10, 12, min(620, toast.get_width() + 16), 24)
            pygame.draw.rect(self.canvas, (32, 50, 44), bg)
            pygame.draw.rect(self.canvas, (191, 168, 120), bg, 1)
            self.canvas.blit(toast, (18, 19))
        self._draw_minimap()

    def _draw_minimap(self) -> None:
        rect = pygame.Rect(551, 10, 78, 58)
        pygame.draw.rect(self.canvas, (34, 52, 49), rect)
        pygame.draw.ellipse(self.canvas, (57, 111, 113), (rect.x + 4, rect.y + 5, 69, 47))
        pygame.draw.ellipse(self.canvas, (116, 147, 87), (rect.x + 7, rect.y + 7, 63, 43))
        pens = LANDMARKS["pens"]["pos"]
        pens_x = rect.x + 7 + int(pens[0] / self.world_width * 63)
        pens_y = rect.y + 7 + int(pens[1] / self.world_height * 43)
        pygame.draw.circle(self.canvas, (100, 227, 211), (pens_x, pens_y), 3)
        pygame.draw.circle(self.canvas, (31, 78, 71), (pens_x, pens_y), 4, 1)
        hatchery = LANDMARKS["hatchery"]["pos"]
        hatchery_x = rect.x + 7 + int(hatchery[0] / self.world_width * 63)
        hatchery_y = rect.y + 7 + int(hatchery[1] / self.world_height * 43)
        pygame.draw.rect(self.canvas, (193, 223, 250), (hatchery_x - 2, hatchery_y - 2, 4, 4))
        market = LANDMARKS["market"]["pos"]
        market_x = rect.x + 7 + int(market[0] / self.world_width * 63)
        market_y = rect.y + 7 + int(market[1] / self.world_height * 43)
        pygame.draw.rect(self.canvas, (248, 224, 145), (market_x - 2, market_y - 2, 4, 4))
        x, y = (self.truck_x, self.truck_y) if self.in_truck else (self.player_x, self.player_y)
        marker_x = rect.x + 7 + int(x / self.world_width * 63)
        marker_y = rect.y + 7 + int(y / self.world_height * 43)
        pygame.draw.rect(self.canvas, (242, 107, 79), (marker_x - 2, marker_y - 2, 4, 4))

    def _draw_objective(self) -> None:
        if self.inside_hatchery:
            stage = str(self.hatchery["stage"]).replace("_", " ").upper()
            count = int(self.hatchery["count"])
            next_task = {
                "empty": "INCUBATOR: LOAD FERTILIZED EGGS",
                "eggs": "INCUBATOR: MONITOR FLOW / WAIT FOR HATCH",
                "alevins": "NURSERY: FEED ALEVIN TANKS",
                "fry": "NURSERY: FEED AND GRADE FRY",
                "smolt_ready": "LAB: VACCINATE THEN GRADE SMOLTS",
            }.get(str(self.hatchery["stage"]), "CHECK THE HATCHERY BATCH")
            if stage == "SMOLT READY" and self.hatchery["vaccinated"] and self.hatchery["graded"]:
                next_task = "GRADER: TRANSFER CERTIFIED SMOLTS TO PENS"
            box = pygame.Rect(10, 45, 320, 42)
            pygame.draw.rect(self.canvas, (30, 61, 54), box)
            pygame.draw.rect(self.canvas, (102, 202, 169), box, 1)
            self._draw_text(self.canvas, f"SMOLT HATCHERY  ·  {stage}  ·  {count:,} FISH", (17, 49), (164, 224, 183), self.small_font)
            self._draw_text(self.canvas, next_task, (17, 65), (255, 242, 203), self.small_font)
            return
        if self.in_truck and self.truck_cargo_kg > 0:
            target_key, heading = "market", "DELIVER FARMED SALMON"
        elif not self.in_truck and self.truck_cargo_kg > 0:
            target_key, heading = "truck", "LOAD DELIVERY TRUCK"
        elif self.hatchery["stage"] != "empty":
            stage = self.hatchery["stage"]
            if stage == "smolt_ready" and self.hatchery["vaccinated"] and self.hatchery["graded"]:
                target_key, heading = "pens", "TRANSFER CERTIFIED SMOLTS TO PENS"
            elif stage == "smolt_ready" and not self.hatchery["vaccinated"]:
                target_key, heading = "hatchery", "VACCINATE THE READY SMOLT BATCH"
            elif stage == "smolt_ready":
                target_key, heading = "hatchery", "GRADE THE VACCINATED SMOLTS"
            else:
                target_key, heading = "hatchery", "CARE FOR THE GROWING SMOLT BATCH"
        else:
            target_key, heading = "pens", "SALMON FARM OBJECTIVE"
        target_x, target_y = LANDMARKS[target_key]["pos"]
        player_x, player_y = (self.truck_x, self.truck_y) if self.in_truck else (self.player_x, self.player_y)
        distance = math.dist((player_x, player_y), (target_x, target_y))
        bearing = math.degrees(math.atan2(target_x - player_x, player_y - target_y)) % 360
        compass = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")[round(bearing / 45) % 8]
        if distance < 125:
            destination = "E  OPEN SALMON PEN OPERATIONS" if target_key == "pens" else "E  ENTER TRUCK" if target_key == "truck" else "E  ENTER SMOLT HATCHERY" if target_key == "hatchery" else "PARK AND PRESS E TO UNLOAD"
        else:
            destination = f"{LANDMARKS[target_key]['name']}  ·  {distance:.0f} M {compass}"
        box = pygame.Rect(10, 45, 320, 42)
        pygame.draw.rect(self.canvas, (30, 61, 54), box)
        pygame.draw.rect(self.canvas, (102, 202, 169), box, 1)
        self._draw_text(self.canvas, heading, (17, 49), (164, 224, 183), self.small_font)
        self._draw_text(self.canvas, destination, (17, 62), (255, 242, 203), self.small_font)
        self._draw_text(self.canvas, "TEAL PENS  ·  BLUE HATCHERY", (17, 75), (187, 220, 239), self.small_font)

    def _draw(self) -> None:
        if self.mode != "career":
            self._draw_shift_frame()
            if self.album_open:
                self._draw_album()
            self._present()
            return
        if not self.inside_hatchery:
            self.camera_x = max(0, min(self.world_width - LOGICAL_SIZE[0], (self.truck_x if self.in_truck else self.player_x) - LOGICAL_SIZE[0] / 2))
            self.camera_y = max(0, min(self.world_height - VIEW_HEIGHT, (self.truck_y if self.in_truck else self.player_y) - VIEW_HEIGHT / 2))
        self._draw_world()
        self._draw_hud()
        self._draw_objective()
        if self.active_panel:
            self._draw_panel()
        if self.show_map:
            self._draw_full_map()
        if self.show_journal:
            self._draw_journal()
        pygame.draw.rect(self.canvas, (24, 49, 54), (0, 384, 640, 16))
        self._draw_text(self.canvas, self._fit_music_text(self._music_status(), 443), (10, 389), font=self.small_font)
        self._draw_text(self.canvas, "B: Album  V: " + ("unmute" if self.audio_muted else "mute"), (458, 389), font=self.small_font)
        if self.album_open:
            self._draw_album()
        self._present()

    def _present(self) -> None:
        window_width, window_height = self.window.get_size()
        scale = min(window_width / LOGICAL_SIZE[0], window_height / LOGICAL_SIZE[1])
        scaled = pygame.transform.scale(self.canvas, (max(1, int(640 * scale)), max(1, int(400 * scale))))
        self.window.fill((12, 25, 27))
        self.window.blit(scaled, ((window_width - scaled.get_width()) // 2, (window_height - scaled.get_height()) // 2))
        pygame.display.flip()

    def _move_player(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        if self.active_panel or self.show_map or self.show_journal:
            return
        if self.inside_hatchery:
            dx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP])
            movement = pygame.Vector2(dx, dy)
            if movement.length_squared() > 0:
                movement = movement.normalize()
                self.interior_x = max(42, min(598, self.interior_x + movement.x * 155 * dt))
                self.interior_y = max(78, min(308, self.interior_y + movement.y * 155 * dt))
                self.player_facing = math.atan2(movement.x, -movement.y)
            return
        dx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP])
        movement = pygame.Vector2(dx, dy)
        if movement.length_squared() == 0:
            self.player_stamina = min(100, self.player_stamina + dt * 8)
            return
        movement = movement.normalize()
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = (210 if running else 142) * (0.5 + .5 * self.player_stamina / 100)
        if self._road_distance(self.player_x, self.player_y) < 34:
            speed *= 1.15
        step_x, step_y = movement.x * speed * dt, movement.y * speed * dt
        self.player_facing = math.atan2(movement.x, -movement.y)
        next_x = self.player_x + step_x
        if self._walkable(next_x, self.player_y):
            self.player_x = next_x
        next_y = self.player_y + step_y
        if self._walkable(self.player_x, next_y):
            self.player_y = next_y
        if running:
            self.player_stamina = max(15, self.player_stamina - dt * 11)
        self._collect_nearby()

    def _nearest_hatchery_station(self) -> tuple[str, float] | None:
        stations = {
            "incubator": (120, 122),
            "nursery": (288, 133),
            "hatchery_lab": (494, 120),
            "grader": (485, 238),
        }
        station, position = min(stations.items(), key=lambda item: math.dist((self.interior_x, self.interior_y), item[1]))
        return station, math.dist((self.interior_x, self.interior_y), position)

    def _walkable(self, x: float, y: float) -> bool:
        if not self._on_island(x, y):
            return False
        for key, landmark in LANDMARKS.items():
            lx, ly = landmark["pos"]
            w, h = landmark["size"]
            if self.mode == "shift" and key == "pens":
                w, h = 320, 200
            if abs(x - lx) < w * .35 and abs(y - ly) < h * .35:
                return False
        return True

    def _move_truck(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        if self.active_panel or self.show_map or self.show_journal:
            return
        gas = keys[pygame.K_w] or keys[pygame.K_UP]
        brake = keys[pygame.K_s] or keys[pygame.K_DOWN]
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        throttle = float(gas) - float(brake)
        road = self._road_distance(self.truck_x, self.truck_y) < 52
        max_speed = (245 if road else 108) * max(.70 if self.mode == "shift" else .45, 1 - self.truck_damage / 135)
        if throttle > 0:
            if self.truck_fuel > 0:
                self.truck_speed = min(max_speed, self.truck_speed + 155 * dt)
                self.truck_fuel = max(0, self.truck_fuel - .11 * dt * (1 + abs(self.truck_speed) / 150))
            else:
                self.truck_speed = max(0, self.truck_speed - 80 * dt)
        elif throttle < 0:
            if self.truck_speed > 10:
                self.truck_speed = max(0, self.truck_speed - 260 * dt)
            else:
                self.truck_speed = max(-65, self.truck_speed - 90 * dt)
        else:
            drag = 30 if road else 85
            if self.truck_speed > 0:
                self.truck_speed = max(0, self.truck_speed - drag * dt)
            elif self.truck_speed < 0:
                self.truck_speed = min(0, self.truck_speed + drag * dt)
        steer = float(right) - float(left)
        if steer and abs(self.truck_speed) > 3:
            grip = .65 if self.weather in ("Storm", "Light rain") else 1.0
            turn_rate = (3.4 if self.mode == "shift" and abs(self.truck_speed) < 90 else 2.8) / (1 + abs(self.truck_speed) / 100)
            self.truck_heading += steer * grip * turn_rate * dt * (1 if self.truck_speed >= 0 else -1)
            self.truck_heading %= math.tau
        direction = pygame.Vector2(math.sin(self.truck_heading), -math.cos(self.truck_heading))
        next_x = self.truck_x + direction.x * self.truck_speed * dt
        next_y = self.truck_y + direction.y * self.truck_speed * dt
        if self._vehicle_clear(next_x, next_y):
            self.truck_x, self.truck_y = next_x, next_y
        else:
            if self.mode == "shift" and self.bump_cooldown <= 0 and abs(self.truck_speed) > 8:
                self.shift_bumps += 1
                self.bump_cooldown = 1.0
            self.truck_speed *= -.18
            self.truck_damage = min(100, self.truck_damage + 3 * dt * (.25 if self.mode == "shift" else 1))
            if abs(self.truck_speed) < 5:
                self.truck_speed = 0
        if not self._on_island(self.truck_x, self.truck_y):
            self.truck_speed *= .7
            self.truck_x -= direction.x * self.truck_speed * dt
            self.truck_y -= direction.y * self.truck_speed * dt

    def _vehicle_clear(self, x: float, y: float) -> bool:
        if not self._on_island(x, y):
            return False
        for key, landmark in LANDMARKS.items():
            if key == "truck":
                continue
            lx, ly = landmark["pos"]
            w, h = landmark["size"]
            if self.mode == "shift" and key == "pens":
                w, h = 500, 330
            if abs(x - lx) < w * .28 and abs(y - ly) < h * .28:
                return False
        return True

    def _collect_nearby(self) -> None:
        if self.mode == "shift":
            return
        item = self._nearest_collectible()
        if not item:
            return
        item["taken"] = True
        kind = str(item["kind"])
        inventory_key = {"shell": "shells", "driftwood": "driftwood", "bait": "bait"}[kind]
        self.inventory[inventory_key] += 1
        self.cash += 20 if kind == "shell" else 0
        self._xp(5)
        self._notify(f"Found {kind}. Beach discoveries are added to your pack.")

    def _interact(self) -> None:
        if self.in_truck:
            if abs(self.truck_speed) > 14:
                self._notify("Slow to a stop before getting out.")
                return
            if self.truck_cargo_kg and math.dist((self.truck_x, self.truck_y), LANDMARKS["market"]["pos"]) < 145:
                self._deliver_cargo()
                return
            self.in_truck = False
            self.player_x = self.truck_x + math.cos(self.truck_heading) * 30
            self.player_y = self.truck_y + math.sin(self.truck_heading) * 30
            self._notify("You stepped out of the truck.")
            self.save()
            return
        if self.inside_hatchery:
            door_distance = math.dist((self.interior_x, self.interior_y), (320, 302))
            if door_distance < 54:
                self.inside_hatchery = False
                self.player_x, self.player_y = self.hatchery_exit_x, self.hatchery_exit_y
                self._notify("You stepped outside the smolt hatchery.")
                self.save()
                return
            station = self._nearest_hatchery_station()
            if station and station[1] < 58:
                self.active_panel = station[0]
                return
            self._notify("Walk closer to an incubator, nursery tank, health lab, grader, or the exit.")
            return
        collectible = self._nearest_collectible()
        if collectible:
            self._collect_nearby()
            return
        nearest = self._nearest_landmark()
        if not nearest or nearest[1] > 110:
            self._notify("Nothing close enough to interact with. Explore the island.")
            return
        key = nearest[0]
        if key == "market" and self.truck_cargo_kg and math.dist((self.truck_x, self.truck_y), LANDMARKS["market"]["pos"]) < 145:
            self._deliver_cargo()
            return
        if key == "truck":
            self.in_truck = True
            self.truck_x, self.truck_y = self.player_x, self.player_y
            self.truck_speed = 0
            self._notify("Truck started. W accelerates, S brakes/reverses, A/D turn the front wheels.")
            return
        if key == "hatchery":
            self.hatchery_exit_x, self.hatchery_exit_y = self.player_x, self.player_y
            self.interior_x, self.interior_y = 320, 293
            self.inside_hatchery = True
            self.active_panel = None
            self._notify("Smolt hatchery entered. Walk to the incubator, nursery, lab, or grader and press E to work.")
            self.save()
            return
        self.active_panel = LANDMARKS[key]["kind"]
        if self.active_panel == "pier":
            self.active_panel = "lighthouse"
        if self.active_panel == "market" and self.truck_cargo_kg > 0:
            self.panel_message = "Drive the truck into the market yard and press E to deliver."
        else:
            self.panel_message = ""

    def _landmark_position(self, key: str) -> tuple[float, float]:
        return LANDMARKS[key]["pos"]

    def _deliver_cargo(self) -> None:
        kg = self.truck_cargo_kg
        if kg <= 0:
            self._notify("No fish cargo to unload. Load fish at the pens.")
            return
        premium = 1 + self.reputation / 1000
        sale = kg * self.market_price * premium
        transport = max(250, 850 + self.truck_damage * 30)
        self.cash += sale - transport
        self.harvested_kg += kg
        self.total_sales += int(sale)
        self.contract["delivered"] += kg
        self.truck_cargo_kg = 0
        self.reputation = min(100, self.reputation + 1)
        self._xp(max(10, int(kg / 100)))
        self._notify(f"Delivered {kg:,.0f} kg for ${sale:,.0f}. Transport and repair costs: ${transport:,.0f}.")
        if self.contract["delivered"] >= self.contract["target"]:
            reward = self.contract["reward"]
            company = self.contract["company"]
            self.cash += reward
            self.reputation = min(100, self.reputation + 4)
            self._xp(80)
            self._notify(f"{company} contract complete! Bonus ${reward:,}; new work added to the board.")
            self.contract = self._new_contract()
        self.save()

    def _new_contract(self) -> dict[str, float | str | int]:
        company, target, reward = random.choice((("Harbor Co-op", 2400, 8500), ("Northshore Grocers", 4200, 16000), ("Fjordline Kitchens", 1800, 7200), ("Blue Current Export", 6200, 28000)))
        return {"company": company, "target": float(target), "delivered": 0.0, "reward": reward}

    def _open(self, key: str) -> None:
        if key.isdigit():
            self._select_option(int(key))
            return
        if key == "escape" or key == "e":
            self.active_panel = None
            self.panel_message = ""
            return
        if key == "space" and self.active_panel == "lighthouse":
            self._fish_press()

    def _hatchery_action(self, station: str, number: int) -> None:
        batch = self.hatchery
        stage = str(batch["stage"])
        if station == "incubator":
            if number == 1:
                if stage != "empty":
                    self._notify("Clear or transfer the current batch before receiving more eggs.")
                elif self.cash < 2500:
                    self._notify("The fertilized egg order costs $2,500.")
                else:
                    self.cash -= 2500
                    batch.update(stage="eggs", count=10000, weeks=0, quality=max(40, (self.water + self.oxygen) // 2), vaccinated=False, graded=False)
                    self._notify("10,000 fertilized salmon eggs entered incubation. Check water flow and return after two farm weeks.")
                    self._xp(15)
            elif number == 2:
                if stage == "empty":
                    self._notify("No batch to test. Receive fertilized eggs first.")
                else:
                    batch["quality"] = max(0, min(100, (self.water + self.oxygen) // 2 + self.upgrades["biofilter"]))
                    self._notify(f"Intake test recorded batch quality at {batch['quality']}%.")
            elif number == 3:
                if stage == "empty":
                    self._notify("Calibrate the flow pump after starting a batch.")
                elif self.cash >= 1000:
                    self.cash -= 1000
                    batch["quality"] = min(100, int(batch["quality"]) + 8)
                    self._notify("Incubator flow pump calibrated. Oxygen exchange improved.")
                else:
                    self._notify("Pump calibration costs $1,000.")
        elif station == "nursery":
            if number == 1 and stage in ("alevins", "fry"):
                if int(batch["feed_kg"]) < 250:
                    self._notify("Nursery feed is low. Order starter feed at this station.")
                else:
                    batch["feed_kg"] = int(batch["feed_kg"]) - 250
                    batch["quality"] = min(100, int(batch["quality"]) + 8)
                    self._notify("Nursery tanks fed and cleaned. Smolt quality improved.")
            elif number == 1:
                self._notify("The nursery feeding routine begins when eggs hatch into alevins.")
            elif number == 2:
                if self.cash >= 1200:
                    self.cash -= 1200
                    batch["feed_kg"] = int(batch["feed_kg"]) + 1500
                    self._notify("1,500 kg of specialist starter feed delivered to the nursery.")
                else:
                    self._notify("A starter-feed delivery costs $1,200.")
        elif station == "hatchery_lab":
            if number == 1 and stage == "smolt_ready":
                if batch["vaccinated"]:
                    self._notify("This batch has already been vaccinated.")
                else:
                    cost = int(batch["count"] * .20)
                    if self.cash >= cost:
                        self.cash -= cost
                        batch["vaccinated"] = True
                        self._notify(f"Veterinary vaccination completed for {int(batch['count']):,} smolts.")
                    else:
                        self._notify(f"Vaccination requires ${cost:,}.")
            elif number == 1:
                self._notify("Vaccination is scheduled when the batch reaches transfer-ready smolt size.")
            elif number == 2:
                if stage == "empty":
                    self._notify("No live batch to screen.")
                elif self.cash >= 500:
                    self.cash -= 500
                    batch["quality"] = min(100, int(batch["quality"]) + 5)
                    self._notify("Health screen clear. The batch quality rating improved.")
                else:
                    self._notify("A lab health screen costs $500.")
        elif station == "grader":
            if number == 1 and stage == "smolt_ready":
                if not batch["vaccinated"]:
                    self._notify("Vaccinate the batch in the health lab before grading for transfer.")
                elif batch["graded"]:
                    self._notify("This batch has already been graded.")
                else:
                    rejected = int(batch["count"] * .03)
                    batch["count"] = int(batch["count"]) - rejected
                    batch["graded"] = True
                    self._notify(f"Size grading complete. {rejected:,} undersized fish were held back.")
            elif number == 1:
                self._notify("The grading flume is for transfer-ready smolts only.")
            elif number == 2:
                if stage != "smolt_ready" or not batch["vaccinated"] or not batch["graded"]:
                    self._notify("Transfer requires ready, vaccinated, graded smolts.")
                elif self.cash < 1200:
                    self._notify("Fish-health certification and transport cost $1,200.")
                else:
                    count = int(batch["count"])
                    old_fish = self.fish
                    new_stock = old_fish + count
                    if new_stock:
                        self.average_weight = (old_fish * self.average_weight + count * .08) / new_stock
                        self.health = round((old_fish * self.health + count * int(batch["quality"])) / new_stock)
                    self.fish = new_stock
                    self.cash -= 1200
                    batch["transferred_total"] = int(batch["transferred_total"]) + count
                    batch.update(stage="empty", count=0, weeks=0, quality=92, vaccinated=False, graded=False)
                    self.reputation = min(100, self.reputation + 2)
                    self._xp(50)
                    self._notify(f"Transferred {count:,} certified smolts from freshwater to the open-water pens.")

    def _select_option(self, number: int) -> None:
        panel = self.active_panel
        if panel in ("incubator", "nursery", "hatchery_lab", "grader"):
            self._hatchery_action(panel, number)
            self.save()
            return
        if panel == "pens":
            if number == 1:
                if self.feed < 750:
                    self._notify("Feed store is empty. Visit the feed mill.")
                else:
                    self.feed -= 750
                    self.health = min(100, self.health + 5)
                    self._notify("The crew fed both pens.")
            elif number == 2:
                if self.cash >= 1200:
                    self.cash -= 1200
                    self.water = min(100, self.water + 18)
                    self._notify("Net cleaning restored water flow.")
            elif number == 3:
                if self.cash >= 1600:
                    self.cash -= 1600
                    self.lice = max(0, self.lice - 28)
                    self.health = min(100, self.health + 3)
                    self._notify("Sea-lice treatment completed.")
            elif number == 4:
                self._notify("Smolts are raised through egg, nursery, vaccination, and grading stages at the hatchery.")
            elif number == 5:
                capacity = self.truck_capacity
                if self.truck_cargo_kg:
                    self._notify("Truck already has cargo. Deliver it before loading again.")
                elif self.fish < 1:
                    self._notify("No fish remain in the pens.")
                else:
                    kg = min(capacity, self.fish * self.average_weight)
                    self.fish -= int(kg / max(.01, self.average_weight))
                    self.truck_cargo_kg = kg
                    self._notify(f"Loaded {kg:,.0f} kg. Find the truck in the farm yard and drive to the market.")
            else:
                self._notify("Not enough cash or feed for that operation.")
        elif panel == "farm":
            keys = ("aeration", "biofilter", "truck", "feed")
            if 1 <= number <= 4:
                key = keys[number - 1]
                cost = (18000, 24000, 16000, 20000)[number - 1] * (self.upgrades[key] + 1)
                if self.cash >= cost and self.upgrades[key] < 5:
                    self.cash -= cost
                    self.upgrades[key] += 1
                    if key == "truck":
                        self.truck_capacity += 1200
                    self._notify(f"{key.title()} upgrade level {self.upgrades[key]} installed.")
                else:
                    self._notify(f"Upgrade requires ${cost:,}; maximum level is 5.")
            elif number == 5:
                cost = 9000 * (self.crew_level + 1)
                if self.cash >= cost and self.crew_level < 10:
                    self.cash -= cost
                    self.crew_level += 1
                    self._notify(f"Crew trained to level {self.crew_level}.")
                else:
                    self._notify(f"Crew training requires ${cost:,}; maximum level is 10.")
        elif panel == "town" and number == 1:
            self._notify("The cove needs steady deliveries. Customer contract is pinned to your journal.")
            self._xp(15)
        elif panel == "mill" and number in (1, 2):
            cost, amount = ((2400, 2000) if number == 1 else (10800, 10000))
            if self.cash >= cost:
                self.cash -= cost
                self.feed += amount
                self._notify(f"Feed mill delivery: {amount:,} kg in the store.")
            else:
                self._notify("Not enough cash for that feed delivery.")
        elif panel == "mill" and number == 3:
            if self.cash >= 400:
                self.cash -= 400
                self.inventory["bait"] += 5
                self._notify("Five bait added to your pack.")
            else:
                self._notify("Not enough cash to buy bait.")
        elif panel == "workshop":
            if number == 1:
                cost = int(self.truck_damage * 95)
                if self.cash >= cost:
                    self.cash -= cost
                    self.truck_damage = 0
                    self._notify(f"Truck repaired for ${cost:,}.")
            elif number == 2 and self.cash >= 4000:
                self.cash -= 4000
                self.truck_damage = 0
                self.truck_fuel = 70
                self._notify("Full service complete. Fuel and condition restored.")
            elif number == 3 and self.cash >= 16000 and self.upgrades["truck"] < 5:
                self.cash -= 16000
                self.upgrades["truck"] += 1
                self.truck_capacity += 1200
                self._notify("Engine and fuel-tank upgrade installed.")
            else:
                self._notify("Service could not be completed. Check funds and upgrade level.")
        elif panel == "forest":
            if number == 1 and self.inventory["driftwood"] >= 5:
                self.inventory["driftwood"] -= 5
                self.cash += 900
                self._notify("Trail crew bought your driftwood for $900.")
            elif number == 2:
                self.reputation = min(100, self.reputation + 1)
                self._xp(15)
                self._notify("You helped the coastal bird count. Reputation increased.")
            else:
                self._notify("Gather more driftwood or choose the bird survey.")
        elif panel == "visitor":
            if number == 1:
                if self.water >= 55 and self.health >= 55:
                    self.reputation = min(100, self.reputation + 2)
                    self.cash += 1500
                    self._xp(25)
                    self._notify("Researchers accepted the sample and paid a small field stipend.")
                else:
                    self._notify("The sample indicates poor conditions. Improve the pens and return.")
            elif number == 2:
                self._notify(f"Field report: health {self.health}%, water {self.water}%, oxygen {self.oxygen}%, lice {self.lice}%.")
        elif panel == "rest" and number == 1:
            self.day_clock = 7.0
            self.player_stamina = 100
            self._advance_week()
        elif panel == "rest" and number == 2:
            self.save()
        else:
            self._notify("Nothing changed. Try another activity.")
        self.save()

    def _fish_press(self) -> None:
        if self.fishing_state == "idle" or self.fishing_state == "caught":
            if self.inventory["bait"] <= 0:
                self._notify("No bait left. The feed mill sells it with supplies.")
                return
            self.inventory["bait"] -= 1
            self.fishing_state = "waiting"
            self.fishing_timer = random.uniform(1.4, 4.5)
            self._notify("Line cast. Watch the bobber.")
        elif self.fishing_state == "bite":
            self.fishing_state = "caught"
            self.inventory["wild_fish"] += 1
            reward = random.randint(180, 650)
            self.cash += reward
            self._xp(12)
            self._notify(f"Nice catch! The harbor paid ${reward} for your fish.")
        elif self.fishing_state == "waiting":
            self._notify("No bite yet. Keep watching the bobber.")

    def _update(self, dt: float) -> None:
        self._sync_music_pause()
        if self.video_open:
            self._update_video(dt)
            return
        if self.album_open or not self.focused:
            return
        if self.mode != "career":
            self._update_shift(dt)
            return
        dt = min(dt, .05)
        keys = pygame.key.get_pressed()
        if self.album_wait_release:
            movement = (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT)
            if any(keys[key] for key in movement):
                return
            self.album_wait_release = False
        if not self.active_panel and not self.show_map and not self.show_journal:
            if self.in_truck:
                self._move_truck(dt, keys)
            else:
                self._move_player(dt, keys)
            self.day_clock += dt * .12
            if self.day_clock >= 24:
                self.day_clock -= 24
                self.player_stamina = min(100, self.player_stamina + 12)
        if self.fishing_state == "waiting":
            self.fishing_timer -= dt
            if self.fishing_timer <= 0:
                self.fishing_state = "bite"
                self.fishing_timer = 1.8
                self._notify("THE FLOAT IS DOWN! REEL NOW!")
        elif self.fishing_state == "bite":
            self.fishing_timer -= dt
            if self.fishing_timer <= 0:
                self.fishing_state = "idle"
                self._notify("The fish got away. Cast again when ready.")
        self.toast_timer = max(0, self.toast_timer - dt)

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._close_video()
        if not self._album_event(event):
            self._handle_game_event(event)
        self._sync_music_pause()

    def _handle_game_event(self, event: pygame.event.Event) -> None:
        if self.mode != "career":
            self._shift_event(event)
            return
        if event.type == pygame.QUIT:
            self.save()
            self.running = False
        elif event.type == pygame.KEYDOWN:
            key = pygame.key.name(event.key)
            if key == "escape":
                if self.active_panel:
                    self.active_panel = None
                elif self.show_map:
                    self.show_map = False
                elif self.show_journal:
                    self.show_journal = False
                elif self.inside_hatchery:
                    self.inside_hatchery = False
                    self.player_x, self.player_y = self.hatchery_exit_x, self.hatchery_exit_y
                    self._notify("You stepped outside the smolt hatchery.")
                    self.save()
                else:
                    self.active_panel = "rest"
            elif key == "e":
                if self.active_panel:
                    self._open("e")
                elif self.show_map or self.show_journal:
                    self.show_map = False
                    self.show_journal = False
                else:
                    self._interact()
            elif key == "m":
                self.show_map = not self.show_map
                self.show_journal = False
                self.active_panel = None
            elif key == "j":
                self.show_journal = not self.show_journal
                self.show_map = False
                self.active_panel = None
            elif key == "i":
                self.active_panel = "rest"
                self.show_map = self.show_journal = False
            elif key in "12345" and self.active_panel:
                self._select_option(int(key))
            elif key == "space" and self.active_panel == "lighthouse":
                self._fish_press()
            elif key == "f5":
                self.save()
            elif key == "f9":
                self._load_saved_or_legacy()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.active_panel:
            if event.pos[1] < 40:
                self.active_panel = None

    def run(self) -> None:
        try:
            while self.running:
                dt = self.clock.tick(60) / 1000
                for event in pygame.event.get():
                    self._handle_event(event)
                self._update(dt)
                self._draw()
        finally:
            self._close_video()
            pygame.quit()


def main() -> None:
    SalmonOpenWorld().run()


if __name__ == "__main__":
    main()
