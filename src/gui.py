"""Valorant Decloak desktop GUI (CustomTkinter).

Runs on a background thread and is fed plain player data from the main loop via a
thread-safe queue. Rebuilds a simple scoreboard table on every update.
"""

import os
import queue

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Rank index -> display name (mirrors NUMBERTORANKS without the ANSI coloring)
RANK_NAMES = [
    "Unranked", "Unranked", "Unranked",
    "Iron 1", "Iron 2", "Iron 3",
    "Bronze 1", "Bronze 2", "Bronze 3",
    "Silver 1", "Silver 2", "Silver 3",
    "Gold 1", "Gold 2", "Gold 3",
    "Platinum 1", "Platinum 2", "Platinum 3",
    "Diamond 1", "Diamond 2", "Diamond 3",
    "Ascendant 1", "Ascendant 2", "Ascendant 3",
    "Immortal 1", "Immortal 2", "Immortal 3",
    "Radiant",
]

# Tier color by rank index (same palette as the console table)
_TIER_COLORS = [
    (46, 46, 46), (46, 46, 46), (46, 46, 46),
    (72, 69, 62), (72, 69, 62), (72, 69, 62),
    (187, 143, 90), (187, 143, 90), (187, 143, 90),
    (174, 178, 178), (174, 178, 178), (174, 178, 178),
    (197, 186, 63), (197, 186, 63), (197, 186, 63),
    (24, 167, 185), (24, 167, 185), (24, 167, 185),
    (216, 100, 199), (216, 100, 199), (216, 100, 199),
    (24, 148, 82), (24, 148, 82), (24, 148, 82),
    (221, 68, 68), (221, 68, 68), (221, 68, 68),
    (255, 253, 205),
]

# (header, pixel width, anchor)
COLUMNS = [
    ("Ajan", 96),
    ("İsim", 210),
    ("Derece", 110),
    ("RR", 55),
    ("Zirve", 130),
    ("HS%", 60),
    ("Kazanma", 95),
    ("K/D", 60),
    ("Seviye", 60),
]

# Only the name column is click-to-copy
NAME_COL_INDEX = next(i for i, (h, _w) in enumerate(COLUMNS) if h == "İsim")

STATE_LABELS = {
    "INGAME": ("Oyunda", "#f12727"),
    "PREGAME": ("Ajan Seçimi", "#67ed4c"),
    "MENUS": ("Menüde", "#eef136"),
    "DISCONNECTED": ("Bağlantı Kesildi", "#999999"),
}

# VALORANT gamemode names (English from the API) -> Turkish
MODE_LABELS = {
    "Competitive": "Dereceli",
    "Unrated": "Derecesiz",
    "Swiftplay": "Hızlı Oyun",
    "Spike Rush": "Spike Rush",
    "Deathmatch": "Ölüm Maçı",
    "Escalation": "Tırmanış",
    "Replication": "Replikasyon",
    "Team Deathmatch": "Takım Ölüm Maçı",
    "Custom Game": "Özel Oyun",
    "Custom": "Özel Oyun",
    "New Map": "Yeni Harita",
    "Snowball Fight": "Kartopu Savaşı",
    "All Random One Site": "Hepsi Rastgele",
}

_BG = "#1a1b1e"
_HEADER_BG = "#26272b"
_ROW_A = "#1f2024"
_ROW_B = "#232428"
_SELF_BG = "#3a3320"


def _hex(rgb):
    return "#%02x%02x%02x" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class DecloakGui:
    def __init__(self, version="1.0"):
        self.version = version
        self._queue = queue.Queue()
        self.root = None
        self._status_lbl = None
        self._mode_lbl = None
        self._table = None
        self._footer = None
        self._copy_seq = 0
        self._last = None  # last payload, so resize/redraw can reuse it

    # ---- called from the data-loop thread ----
    def submit(self, state, gamemode, heartbeat_data):
        """Thread-safe: hand a snapshot to the GUI thread."""
        self._queue.put((state, gamemode, heartbeat_data))

    # ---- runs on its own thread ----
    def run(self):
        self.root = ctk.CTk()
        self.root.title("Decloak")
        self.root.geometry("1000x620")
        self.root.minsize(820, 400)
        self.root.configure(fg_color=_BG)
        # Closing the window kills the whole app (console is hidden in GUI mode)
        self.root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

        # Shared fonts: title in Courier New, nicks bold, everything else normal
        self._f_title = ctk.CTkFont(family="Courier New", size=22, weight="bold")
        self._f_status = ctk.CTkFont(family="Segoe UI", size=16)
        self._f_name = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self._f_cell = ctk.CTkFont(family="Segoe UI", size=13)
        self._f_footer = ctk.CTkFont(family="Segoe UI", size=12)
        self._f_ph = ctk.CTkFont(family="Segoe UI", size=15)

        self._build_header()

        self._table = ctk.CTkScrollableFrame(self.root, fg_color=_BG)
        self._table.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        self._footer = ctk.CTkLabel(
            self.root, text="HS ve KD son maçı gösterir.",
            text_color="#777777", font=self._f_footer,
        )
        self._footer.pack(fill="x", padx=14, pady=(0, 8))

        self._show_placeholder("VALORANT bekleniyor...")

        self._poll()
        self.root.mainloop()

    def _copy(self, text):
        text = (text or "").strip()
        if not text or self.root is None:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            return
        if self._footer is not None:
            self._footer.configure(text=f"Kopyalandı: {text}", text_color="#67ed4c")
            self._copy_seq = getattr(self, "_copy_seq", 0) + 1
            seq = self._copy_seq

            def _reset():
                if self._footer is not None and seq == self._copy_seq:
                    self._footer.configure(
                        text="HS ve KD son maçı gösterir.",
                        text_color="#777777", font=self._f_footer,
                    )

            self.root.after(1300, _reset)

    def _build_header(self):
        bar = ctk.CTkFrame(self.root, fg_color=_HEADER_BG, corner_radius=12)
        bar.pack(fill="x", padx=12, pady=12)
        # 3 columns: empty | centered title | right-aligned status
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_columnconfigure(1, weight=0)
        bar.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            bar, text="Valorant Decloak", font=self._f_title
        ).grid(row=0, column=1, pady=10)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e", padx=(6, 16))
        self._status_lbl = ctk.CTkLabel(
            right, text="Bağlanıyor...", font=self._f_status
        )
        self._status_lbl.pack(side="right", pady=10)
        self._mode_lbl = ctk.CTkLabel(
            right, text="", text_color="#aaaaaa", font=self._f_cell
        )
        self._mode_lbl.pack(side="right", padx=(0, 10), pady=10)

    def _poll(self):
        latest = None
        try:
            while True:
                latest = self._queue.get_nowait()
        except queue.Empty:
            pass
        if latest is not None:
            self._last = latest
            try:
                self._render(*latest)
            except Exception as e:  # never let a render bug kill the GUI loop
                self._show_placeholder(f"Çizim hatası: {e}")
        if self.root is not None:
            self.root.after(250, self._poll)

    # ---- rendering ----
    def _clear_table(self):
        for child in self._table.winfo_children():
            child.destroy()

    def _show_placeholder(self, text):
        self._clear_table()
        ctk.CTkLabel(
            self._table, text=text, text_color="#888888",
            font=ctk.CTkFont(size=15),
        ).pack(pady=40)

    def _render(self, state, gamemode, hb):
        label, color = STATE_LABELS.get(state, (state or "?", "#ffffff"))
        if self._status_lbl is not None:
            self._status_lbl.configure(text=label, text_color=color)
        if self._mode_lbl is not None:
            self._mode_lbl.configure(text=MODE_LABELS.get(gamemode, gamemode or ""))

        players = hb.get("players", {}) if isinstance(hb, dict) else {}
        self_puuid = hb.get("puuid") if isinstance(hb, dict) else None

        self._clear_table()
        if not players:
            self._show_placeholder("Henüz oyuncu yok.")
            return

        for col, (title, width) in enumerate(COLUMNS):
            self._table.grid_columnconfigure(col, minsize=width, weight=0)

        header = COLUMNS
        for col, (title, _w) in enumerate(header):
            ctk.CTkLabel(
                self._table, text=title, font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#cfcfcf", fg_color=_HEADER_BG, corner_radius=4,
            ).grid(row=0, column=col, sticky="nsew", padx=1, pady=(0, 4), ipady=4)

        # Show team headers when there are real teams (1 in agent select, 2 in a
        # match). Deathmatch has many distinct teams (everyone solo) -> flat list.
        items = list(players.items())
        # unique teams, preserving first-seen order
        distinct_teams = [
            t for t in dict.fromkeys(p.get("team") for _, p in items) if t
        ]

        # Fixed mapping so the same team always gets the same label everywhere
        # (agent select shows whichever team we are: Takım A or Takım B).
        TEAM_LABELS = {"Blue": "Takım A", "Red": "Takım B"}
        TEAM_COLORS = {"Blue": "#4c97ed", "Red": "#ee4d4d"}
        # Starting side (only shown in agent select): Blue defends, Red attacks
        SIDE_LABELS = {"Blue": "Savunma", "Red": "Atak"}

        def _order(team):
            return {"Blue": 0, "Red": 1}.get(team, 2)

        row_idx = 1
        if 1 <= len(distinct_teams) <= 2:
            ordered = sorted(distinct_teams, key=_order)
            for idx, team in enumerate(ordered):
                label = TEAM_LABELS.get(team, f"Takım {chr(ord('A') + idx)}")
                if state == "PREGAME":
                    side = SIDE_LABELS.get(team)
                    if side:
                        label = f"{label} - {side}"
                self._render_team_header(
                    row_idx, label, TEAM_COLORS.get(team, "#cfcfcf")
                )
                row_idx += 1
                stripe = 0
                for puuid, p in items:
                    if p.get("team") != team:
                        continue
                    is_self = (puuid == self_puuid)
                    bg = _SELF_BG if is_self else (_ROW_A if stripe % 2 else _ROW_B)
                    self._render_row(row_idx, puuid, p, is_self, bg)
                    row_idx += 1
                    stripe += 1
        else:
            for puuid, p in items:
                is_self = (puuid == self_puuid)
                bg = _SELF_BG if is_self else (_ROW_A if row_idx % 2 else _ROW_B)
                self._render_row(row_idx, puuid, p, is_self, bg)
                row_idx += 1

    def _render_team_header(self, row, text, color):
        ctk.CTkLabel(
            self._table, text=text, anchor="center",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=color, fg_color=_HEADER_BG, corner_radius=4,
        ).grid(
            row=row, column=0, columnspan=len(COLUMNS),
            sticky="nsew", padx=1, pady=(8, 2), ipady=4,
        )

    def _render_row(self, row, puuid, p, is_self, bg):
        rank_idx = _safe_int(p.get("rank"), 0)
        peak_idx = _safe_int(p.get("peakRank"), 0)
        team = p.get("team")

        if is_self:
            name_color = "#dde029"
        elif team == "Red":
            name_color = "#ee4d4d"
        elif team == "Blue":
            name_color = "#4c97ed"
        else:
            name_color = "#dddddd"

        rank_color = _hex(_TIER_COLORS[rank_idx]) if 0 <= rank_idx < len(_TIER_COLORS) else "#ffffff"
        peak_color = _hex(_TIER_COLORS[peak_idx]) if 0 <= peak_idx < len(_TIER_COLORS) else "#ffffff"

        rr = _safe_int(p.get("rr"), 0)
        rr_color = "#12cc19" if rr > 0 else ("#f12727" if rr < 0 else "#ffffff")

        rank_text = RANK_NAMES[rank_idx] if 0 <= rank_idx < len(RANK_NAMES) else "?"
        peak_text = (RANK_NAMES[peak_idx] if 0 <= peak_idx < len(RANK_NAMES) else "?") + (p.get("peakRankAct") or "")

        hs = p.get("headshotPercentage")
        hs_text = f"{hs}%" if hs not in (None, "") else "-"
        wr_text = p.get("winPercentage") or "-"
        kd_text = str(p.get("kd", "-"))
        lvl_text = str(p.get("level", "-"))
        agent_text = p.get("agent", "") or ""
        name_text = p.get("name", "") or "?"

        cells = [
            (agent_text, "#dddddd"),
            (name_text, name_color),
            (rank_text, rank_color),
            (str(rr), rr_color),
            (peak_text, peak_color),
            (hs_text, "#dddddd"),
            (wr_text, "#dddddd"),
            (kd_text, "#dddddd"),
            (lvl_text, "#dddddd"),
        ]

        weight = "bold" if is_self else "normal"
        for col, (text, fg) in enumerate(cells):
            lbl = ctk.CTkLabel(
                self._table, text=text, text_color=fg, fg_color=bg,
                anchor="center", corner_radius=0,
                font=ctk.CTkFont(size=13, weight=weight),
            )
            lbl.grid(row=row, column=col, sticky="nsew", padx=1, pady=1, ipady=3)
            if text and col == NAME_COL_INDEX:
                lbl.configure(cursor="hand2")
                lbl.bind("<Button-1>", lambda e, t=text: self._copy(t))
