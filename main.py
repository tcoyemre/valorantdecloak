import asyncio
import ctypes
import os
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3
from colr import color as colr
from InquirerPy import inquirer
from rich.console import Console as RichConsole

from src.colors import Colors
from src.config import Config
from src.configurator import configure
from src.constants import *
from src.content import Content
from src.errors import Error
from src.Loadouts import Loadouts
from src.logs import Logging
from src.names import Names
from src.player_stats import PlayerStats
from src.premades import Premades
from src.presences import Presences
from src.rank import Rank
from src.requestsV import Requests
from src.rpc import Rpc
from src.server import Server
from src.states.coregame import Coregame
from src.states.menu import Menu
from src.states.pregame import Pregame
from src.stats import Stats
from src.table import Table
from src.websocket import Ws
from src.os_info import get_os
from src import webserver
from src import panel_window

from src.account_manager.account_manager import AccountManager
from src.account_manager.account_config import AccountConfig
from src.account_manager.account_auth import AccountAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# When built as a windowed (Win32GUI) app there is no console: sys.stdout/stderr
# are None, so make every print()/traceback call a safe no-op instead of crashing.
if sys.stdout is None or sys.stderr is None:
    _devnull = open(os.devnull, "w", encoding="utf-8", errors="ignore")
    if sys.stdout is None:
        sys.stdout = _devnull
    if sys.stderr is None:
        sys.stderr = _devnull


# --panel-view: bu süreç yalnızca paneli gösteren webview penceresidir (ayrı
# çocuk süreç). pywebview ana thread şartı koştuğu için panel ana uygulamadan
# ayrı bir süreçte açılır; burada erkenden yakalayıp lisans/uygulama mantığına
# hiç girmeden pencereyi çalıştırıp çıkarız. Bkz. src/panel_window.py.
if "--panel-view" in sys.argv:
    _pv = sys.argv.index("--panel-view")
    _url = sys.argv[_pv + 1] if _pv + 1 < len(sys.argv) else "http://127.0.0.1:1100/"
    _parent = None
    if "--parent" in sys.argv:
        try:
            _parent = int(sys.argv[sys.argv.index("--parent") + 1])
        except Exception:
            _parent = None
    sys.exit(panel_window.run_viewer(_url, _parent))


def _has_console():
    try:
        return bool(ctypes.windll.kernel32.GetConsoleWindow())
    except Exception:
        return False


def _set_console_title(title):
    """Set the console title without spawning a cmd window (works with no console too)."""
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        pass


def clear_console():
    if _has_console():
        os.system("cls")


def _set_console_visible(visible: bool):
    """Hide/show the console window so only the GUI is shown in GUI mode."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 1 if visible else 0)
    except Exception:
        pass


def _show_error_box(text):
    try:
        ctypes.windll.user32.MessageBoxW(0, str(text), "Valorant Decloak - Hata", 0x10)
    except Exception:
        pass


def _show_info_box(text):
    try:
        # 0x40 = MB_ICONINFORMATION (bilgi/uyarı simgesi, hata değil)
        ctypes.windll.user32.MessageBoxW(0, str(text), "Valorant Decloak - Bilgi", 0x40)
    except Exception:
        pass


def _is_valorant_running():
    """VALORANT oyun süreci çalışıyor mu? Kapanan oyunu hata sanmamak için."""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq VALORANT-Win64-Shipping.exe", "/FO", "CSV", "/NH"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).decode().lower()
        return "valorant-win64-shipping.exe" in output
    except Exception:
        # Tespit edemiyorsak çalışıyor varsay (hatayı normal hata gibi göster).
        return True


# Not: Eski tkinter kontrol penceresi (_start_control_window) kaldırıldı. Artık
# kontrol görevini panelin kendi webview penceresi görüyor: pencere kapatılınca
# panel_window.open(on_close=...) ile tüm program kapanır. Bkz. src/panel_window.py.


_set_console_title("Decloak")

server = ""


def program_exit(status: int):  # so we don't need to import the entire sys module
    log(f"exited program with error code {status}")
    raise sys.exit(status)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(("10.254.254.254", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


# VALORANT GamePodID datacenter codes -> human-friendly city names
SERVER_CITIES = {
    "frankfurt": "Frankfurt", "fra": "Frankfurt",
    "london": "London", "lhr": "London", "ldn": "London",
    "paris": "Paris", "cdg": "Paris", "par": "Paris",
    "stockholm": "Stockholm", "arn": "Stockholm",
    "madrid": "Madrid", "mad": "Madrid",
    "milan": "Milan", "mil": "Milan", "mxp": "Milan",
    "warsaw": "Warsaw", "waw": "Warsaw",
    "istanbul": "İstanbul", "ist": "İstanbul", "isb": "İstanbul",
    "bahrain": "Bahrain", "bhr": "Bahrain", "bah": "Bahrain",
    "dubai": "Dubai", "dxb": "Dubai",
    "tokyo": "Tokyo", "tyo": "Tokyo", "nrt": "Tokyo",
    "osaka": "Osaka", "kix": "Osaka",
    "seoul": "Seoul", "icn": "Seoul",
    "hongkong": "Hong Kong", "hkg": "Hong Kong",
    "singapore": "Singapore", "sgp": "Singapore", "sin": "Singapore",
    "sydney": "Sydney", "syd": "Sydney",
    "mumbai": "Mumbai", "bom": "Mumbai",
    "saopaulo": "São Paulo", "gru": "São Paulo", "sao": "São Paulo",
    "santiago": "Santiago", "scl": "Santiago",
    "oregon": "Oregon", "pdx": "Oregon",
    "ohio": "Ohio", "cmh": "Ohio",
    "virginia": "Virginia", "iad": "Virginia", "ashburn": "Virginia",
    "california": "California", "sjc": "California",
    "texas": "Texas", "dfw": "Texas",
    "atlanta": "Atlanta", "atl": "Atlanta",
    "chicago": "Chicago", "ord": "Chicago",
    "miami": "Miami", "mia": "Miami",
}


def server_city(gamepod):
    """Extract a friendly city name from a GamePodID (e.g. ...-fra1-1... -> Frankfurt)."""
    if not gamepod:
        return ""
    for tok in re.split(r"[^a-z0-9]+", gamepod.lower()):
        if tok in SERVER_CITIES:
            return SERVER_CITIES[tok]
        base = tok.rstrip("0123456789")  # 'fra1' -> 'fra'
        if base and base in SERVER_CITIES:
            return SERVER_CITIES[base]
    return ""


try:
    Logging = Logging()
    log = Logging.log

    # OS Logging
    log(f"Operating system: {get_os()}\n")

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--config":
            # The interactive configurator needs a console; allocate one if the
            # windowed build was launched with --config.
            if not _has_console():
                try:
                    ctypes.windll.kernel32.AllocConsole()
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="ignore")
                    sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="ignore")
                except Exception:
                    pass
            configure()
            run_app = inquirer.confirm(
                message="Valorant Decloak şimdi çalışsın mı?", default=True
            ).execute()
            if run_app:
                clear_console()
            else:
                os._exit(0)
        else:
            clear_console()
    except Exception as e:
        print("Ayarlar çalıştırılırken bir hata oluştu!")
        log(f"configurator encountered an error")
        log(str(traceback.format_exc()))
        if _has_console():
            input("çıkmak için enter'a basın...\n")
        else:
            _show_error_box("Ayarlar hatası. logs klasörüne bakın.")
        os._exit(1)

    acc_manager = AccountManager(log, AccountConfig, AccountAuth, NUMBERTORANKS)

    ErrorSRC = Error(log, acc_manager)

    # Update/status checks disabled (Valorant Decloak fork uses its own versioning)
    # Requests.check_version(version, Requests.copy_run_update_script)
    # Requests.check_status()
    Requests = Requests(version, log, ErrorSRC)

    cfg = Config(log)

    content = Content(Requests, log)

    rank = Rank(Requests, log, content, before_ascendant_seasons)
    pstats = PlayerStats(Requests, log, cfg)

    namesClass = Names(Requests, log, cfg)

    presences = Presences(Requests, log)

    menu = Menu(Requests, log, presences)
    pregame = Pregame(Requests, log)
    coregame = Coregame(Requests, log)

    # Gerçek premade tespiti (geçmiş maçların partyId'lerinden, pd API).
    premades = Premades(Requests, log, webserver, depth=3)

    Server = Server(log, ErrorSRC)
    # Mobile/web server disabled
    # Server.start_server()

    # Local web panel: runs in the background, viewed in the browser at localhost.
    web_port = cfg.port
    try:
        webserver.start(
            web_port,
            on_quit=lambda: (panel_window.close(), os._exit(0)),
            # Panel dili değişince Discord RPC'yi de aynı dile geçir.
            on_lang=lambda l: rpc.set_lang(l) if rpc is not None else None,
        )
        log(f"web panel serving on http://127.0.0.1:{web_port}")
        lan_ip = webserver.get_lan_ip()
        if lan_ip:
            log(f"web panel also reachable on the local network at http://{lan_ip}:{web_port}")
        # Panel kendi penceresinde açılır; kullanıcı pencereyi kapatınca tüm
        # program kapanır (on_close). Ayrı bir tkinter kontrol penceresi yok.
        panel_window.open(
            f"http://127.0.0.1:{web_port}/",
            title="Valorant Decloak",
            on_close=lambda: os._exit(0),
            log=log,
        )
    except Exception as e:
        log(f"web server failed to start: {e}")
    _set_console_visible(False)

    agent_dict = content.get_all_agents()

    map_info = content.get_all_maps()
    map_urls = content.get_map_urls(map_info)
    map_splashes = content.get_map_splashes(map_info)

    current_map = coregame.get_current_map(map_urls, map_splashes)

    colors = Colors(log, hide_names, agent_dict, AGENTCOLORLIST)

    loadoutsClass = Loadouts(Requests, log, colors, Server, current_map)
    table = Table(cfg, log)

    stats = Stats()

    if cfg.get_feature_flag("discord_rpc"):
        rpc = Rpc(map_urls, gamemodes, colors, log)
    else:
        rpc = None

    Wss = Ws(Requests.lockfile, Requests, cfg, colors, hide_names, Server, rpc)
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_forever()

    log(f"Valorant Decloak v{version}")

    valoApiSkins = requests.get("https://valorant-api.com/v1/weapons/skins")
    gameContent = content.get_content()
    seasonID = content.get_latest_season_id(gameContent)
    previousSeasonID = content.get_previous_season_id(gameContent)
    pstats.season_id = seasonID  # aggregate stats over the current season
    lastGameState = ""

    # Cache rank+stats per player for the current match so PREGAME data can be reused in INGAME
    match_player_cache = {
        "match_id": None,
        "players": {},  # puuid -> {"playerRank", "previousPlayerRank", "ppstats", "ts"}
    }
    MATCH_PLAYER_CACHE_TTL_SECONDS = 300  # safety TTL

    def reset_match_player_cache(match_id=None):
        match_player_cache["match_id"] = match_id
        match_player_cache["players"] = {}

    def ensure_match_player_cache(match_id):
        if not match_id:
            return

        # New match => reset cache
        if match_player_cache["match_id"] != match_id:
            reset_match_player_cache(match_id)
            return

        # TTL cleanup (safety)
        now = time.time()
        expired = []
        for puuid, cached in match_player_cache["players"].items():
            ts = cached.get("ts", now)
            if (now - ts) > MATCH_PLAYER_CACHE_TTL_SECONDS:
                expired.append(puuid)

        for puuid in expired:
            del match_player_cache["players"][puuid]

    def get_or_fetch_rank_and_stats(player_subject, current_match_id, player_name=None):
        if current_match_id:
            ensure_match_player_cache(current_match_id)
            cached = match_player_cache["players"].get(player_subject)
            if cached is not None:
                return (
                    cached["playerRank"],
                    cached["previousPlayerRank"],
                    cached["ppstats"],
                )

        # Cache miss -> fetch
        playerRank = rank.get_rank(player_subject, seasonID)
        previousPlayerRank = rank.get_rank(player_subject, previousSeasonID)
        ppstats = pstats.get_stats(player_subject, player_name)

        if current_match_id and match_player_cache["match_id"] == current_match_id:
            match_player_cache["players"][player_subject] = {
                "playerRank": dict(playerRank) if isinstance(playerRank, dict) else playerRank,
                "previousPlayerRank": dict(previousPlayerRank) if isinstance(previousPlayerRank, dict) else previousPlayerRank,
                "ppstats": dict(ppstats) if isinstance(ppstats, dict) else ppstats,
                "ts": time.time(),
            }

        return playerRank, previousPlayerRank, ppstats

    def prefetch_player_data(players, names):
        """Warm the rank (MMR) and tracker.gg caches for every player in parallel.

        Each player needs two independent, I/O-bound network calls:
          - rank.get_request(puuid)  -> caches in rank.requestMap[puuid]
          - pstats.get_stats(puuid)  -> caches in pstats.stats_cache[puuid]
        Both write to their own per-puuid dict cache, so running them across a
        thread pool only turns sequential round-trips into concurrent ones - no
        shared state is mutated unsafely. The render loop afterwards reads
        straight from the warm caches, making it effectively instant.
        The slowest call by far is tracker.gg (external, long timeout), so
        firing all of them at once is where most of the speedup comes from.
        """
        seen = set()
        targets = []
        for p in players:
            subject = p.get("Subject")
            if not subject or subject in seen:
                continue
            seen.add(subject)
            targets.append((subject, names.get(subject)))

        if not targets:
            return

        # Make sure auth headers exist once up front so worker threads don't all
        # race to refresh entitlements when headers are empty.
        try:
            Requests.get_headers()
        except Exception:
            pass

        def _warm(target):
            subject, name = target
            try:
                rank.get_request(subject)
            except Exception as e:
                log(f"prefetch rank error for {subject}: {e}")
            try:
                pstats.get_stats(subject, name)
            except Exception as e:
                log(f"prefetch stats error for {subject}: {e}")

        workers = min(12, len(targets))
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                list(ex.map(_warm, targets))
        except Exception as e:
            # Never let prefetch break the main flow; the loop will just fetch
            # any missing player serially as before.
            log(f"prefetch pool error: {e}")

    richConsole = RichConsole()

    firstTime = True
    firstPrint = True
    while True:
        table.clear()
        table.set_default_field_names()
        table.reset_runtime_col_flags()

        # check if short ranks should be used
        if cfg.get_feature_flag("short_ranks"):
            Ranks = SHORT_NUMBERTORANKS
        else:
            Ranks = NUMBERTORANKS

        try:

            # loop = asyncio.get_event_loop()
            # loop.run_until_complete(Wss.conntect_to_websocket())
            # if firstTime:
            #     loop = asyncio.new_event_loop()
            #     asyncio.set_event_loop(loop)
            #     game_state = loop.run_until_complete(Wss.conntect_to_websocket(game_state))
            if firstTime:
                run = True
                while run:
                    presence = presences.get_presence()
                    private_presence = presences.get_private_presence(presence)
                    # wait until your own valorant presence is initialized
                    if private_presence is not None:
                        if cfg.get_feature_flag("discord_rpc"):
                            rpc.set_rpc(private_presence)
                        game_state = presences.get_game_state(presence)
                        if game_state is not None:
                            run = False
                    time.sleep(2)
                log(f"first game state: {game_state}")
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                previous_game_state = game_state
                game_state = loop.run_until_complete(
                    Wss.recconect_to_websocket(game_state)
                )
                # We invalidate the cached responses when going from any state to menus
                if previous_game_state != game_state and game_state == "MENUS":
                    rank.invalidate_cached_responses()
                    reset_match_player_cache()
                    if hasattr(pstats, "clear_runtime_cache"):
                        pstats.clear_runtime_cache()
                log(f"new game state: {game_state}")
                loop.close()
            firstTime = False
            # loop = asyncio.new_event_loop()
            # asyncio.set_event_loop(loop)
            # loop.run_until_complete()
        except TypeError:
            game_state = "DISCONNECTED"
            reset_match_player_cache()
            if hasattr(pstats, "clear_runtime_cache"):
                pstats.clear_runtime_cache()

        if game_state == "DISCONNECTED":
            webserver.update({"state": "DISCONNECTED", "players": {}})
            richConsole.print("[yellow]Disconnected from Valorant. Attempting to reconnect...[/yellow]")
            # Loop waits for the Valorant client to respond
            while True:
                # Rereads the lockfile
                Requests.lockfile = Requests.get_lockfile()

                if Requests.lockfile is None:
                    time.sleep(5)
                    continue

                presence_check = presences.get_presence()
                
                if presence_check is not None:
                    break 
                
                time.sleep(5)

            richConsole.print("[green]Reconnected successfully! Loading...[/green]")
            
            Requests.get_headers(refresh=True)

            Wss = Ws(Requests.lockfile, Requests, cfg, colors, hide_names, Server, rpc)

            firstTime = True 
            lastGameState = ""
            reset_match_player_cache()
            if hasattr(pstats, "clear_runtime_cache"):
                pstats.clear_runtime_cache()
            continue

        if True:
            log(f"getting new {game_state} scoreboard")
            lastGameState = game_state
            game_state_dict = {
                "INGAME": color("In-Game", fore=(241, 39, 39)),
                "PREGAME": color("Agent Select", fore=(103, 237, 76)),
                "MENUS": color("In-Menus", fore=(238, 241, 54)),
            }

            if (not firstPrint) and cfg.get_feature_flag("pre_cls"):
                clear_console()

            is_leaderboard_needed = False
            
            # get new presence
            presence = presences.get_presence()
            priv_presence = presences.get_private_presence(presence)
            
            # Temp fix: Riot is swapping between nested and flat API structures.
            party_state = ""
            if "partyPresenceData" in priv_presence: # Check for nested structure
                party_state = priv_presence["partyPresenceData"]["partyState"]
            elif "partyState" in priv_presence: # Check for flattened structure
                party_state = priv_presence["partyState"]
            else:
                # No known structure found, log and fail
                log("ERROR: Unknown presence API structure in 'main'.")
                party_state = priv_presence["partyPresenceData"]["partyState"]
            
            if (
                priv_presence["provisioningFlow"] == "CustomGame"
                or party_state == "CUSTOM_GAME_SETUP"
            ):
                gamemode = "Custom Game"
            else:
                gamemode = gamemodes.get(priv_presence["queueId"])

            heartbeat_data = {
                "time": int(time.time()),
                "state": game_state,
                "mode": gamemode,
                "puuid": Requests.puuid,
                "players": {},
            }

            if game_state == "INGAME":
                coregame_stats = coregame.get_coregame_stats()
                if coregame_stats == None:
                    continue
                coregame_match_id = coregame.get_coregame_match_id()
                ensure_match_player_cache(coregame_match_id)
                Players = coregame_stats["Players"]
                # data for chat to function
                partyMembers = menu.get_party_members(Requests.puuid, presence)
                partyMembersList = [a["Subject"] for a in partyMembers]

                players_data = {}
                players_data.update({"ignore": partyMembersList})
                for player in Players:
                    if player["Subject"] == Requests.puuid:
                        if cfg.get_feature_flag("discord_rpc"):
                            rpc.set_data({"agent": player["CharacterID"]})
                    players_data.update(
                        {
                            player["Subject"]: {
                                "team": player["TeamID"],
                                "agent": player["CharacterID"],
                                "streamer_mode": player["PlayerIdentity"]["Incognito"],
                            }
                        }
                    )
                Wss.set_player_data(players_data)

                server = coregame_stats.get("GamePodID", "")
                presences.wait_for_presence(namesClass.get_players_puuid(Players))
                names = namesClass.get_names_from_puuids(Players)
                # Warm rank + stats caches for everyone in parallel before the
                # serial render loop, so each player renders from cache instantly.
                prefetch_player_data(Players, names)
                loadouts_arr = loadoutsClass.get_match_loadouts(
                    coregame_match_id,
                    Players,
                    cfg.weapon,
                    valoApiSkins,
                    names,
                    state="game",
                )
                loadouts = loadouts_arr[0]
                loadouts_data = loadouts_arr[1]
                # with alive_bar(total=len(Players), title='Fetching Players', bar='classic2') as bar:
                isRange = False
                playersLoaded = 1

                heartbeat_data["map"] = (map_urls[coregame_stats["MapID"].lower()],)
                _map_name = map_urls.get(coregame_stats["MapID"].lower())
                heartbeat_data["map_name"] = _map_name
                heartbeat_data["map_image"] = map_splashes.get(_map_name)
                with richConsole.status("Loading Players...") as status:
                    partyOBJ = menu.get_party_json(
                        namesClass.get_players_puuid(Players), presence
                    )
                    # log(f"retrieved names dict: {names}")
                    Players.sort(
                        key=lambda Players: Players["PlayerIdentity"].get(
                            "AccountLevel"
                        ),
                        reverse=True,
                    )
                    Players.sort(key=lambda Players: Players["TeamID"], reverse=True)
                    partyCount = 0
                    partyNum = 0
                    partyIcons = {}
                    lastTeamBoolean = False
                    lastTeam = "Red"

                    already_played_with = []
                    stats_data = stats.read_data()

                    for p in Players:
                        if p["Subject"] == Requests.puuid:
                            allyTeam = p["TeamID"]
                    for player in Players:
                        status.update(
                            f"Loading players... [{playersLoaded}/{len(Players)}]"
                        )
                        playersLoaded += 1

                        if player["Subject"] in stats_data.keys():
                            if (
                                player["Subject"] != Requests.puuid
                                and player["Subject"] not in partyMembersList
                            ):
                                curr_player_stat = stats_data[player["Subject"]][-1]
                                i = 1
                                while (
                                    curr_player_stat["match_id"] == coregame.match_id
                                    and len(stats_data[player["Subject"]]) > i
                                ):
                                    i += 1
                                    # if curr_player_stat["match_id"] == coregame.match_id and len(stats_data[player["Subject"]]) > 1:
                                    curr_player_stat = stats_data[player["Subject"]][-i]
                                if curr_player_stat["match_id"] != coregame.match_id:
                                    # checking for party memebers and self players
                                    times = 0
                                    m_set = ()
                                    for m in stats_data[player["Subject"]]:
                                        if (
                                            m["match_id"] != coregame.match_id
                                            and m["match_id"] not in m_set
                                        ):
                                            times += 1
                                            m_set += (m["match_id"],)
                                    if player["PlayerIdentity"]["Incognito"] == False:
                                        already_played_with.append(
                                            {
                                                "times": times,
                                                "name": curr_player_stat["name"],
                                                "agent": curr_player_stat["agent"],
                                                "time_diff": time.time()
                                                - curr_player_stat["epoch"],
                                            }
                                        )
                                    else:
                                        if player["TeamID"] == allyTeam:
                                            team_string = "your"
                                        else:
                                            team_string = "enemy"
                                        already_played_with.append(
                                            {
                                                "times": times,
                                                "name": agent_dict.get(
                                                    player["CharacterID"].lower(), "Unknown"
                                                )
                                                + " on "
                                                + team_string
                                                + " team",
                                                "agent": curr_player_stat["agent"],
                                                "time_diff": time.time()
                                                - curr_player_stat["epoch"],
                                            }
                                        )

                        party_icon = ""
                        partyNum = 0
                        # set party premade icon
                        for party in partyOBJ:
                            if player["Subject"] in partyOBJ[party]:
                                if party not in partyIcons:
                                    partyIcons.update(
                                        {party: PARTYICONLIST[partyCount]}
                                    )
                                    # PARTY_ICON
                                    party_icon = PARTYICONLIST[partyCount]
                                    partyNum = partyCount + 1
                                    partyCount += 1
                                else:
                                    # PARTY_ICON
                                    party_icon = partyIcons[party]
                                    partyNum = PARTYICONLIST.index(party_icon) + 1
                        playerRank, previousPlayerRank, ppstats = get_or_fetch_rank_and_stats(
                            player["Subject"], coregame_match_id, names.get(player["Subject"])
                        )

                        if player["Subject"] == Requests.puuid:
                            if cfg.get_feature_flag("discord_rpc"):
                                rpc.set_data(
                                    {
                                        "rank": playerRank["rank"],
                                        "rank_name": colors.escape_ansi(
                                            NUMBERTORANKS[playerRank["rank"]]
                                        )
                                        + " | "
                                        + str(playerRank["rr"])
                                        + "rr",
                                    }
                                )
                        # rankStatus = playerRank[1]
                        # useless code since rate limit is handled in the requestsV
                        # while not rankStatus:
                        #     print("You have been rate limited, 😞 waiting 10 seconds!")
                        #     time.sleep(10)
                        #     playerRank = rank.get_rank(player["Subject"], seasonID)
                        #     rankStatus = playerRank[1]

                        hs = ppstats["hs"]
                        kd = ppstats["kd"]

                        rr_numeric_value = ppstats["RankedRatingEarned"]
                        afk_penalty = ppstats["AFKPenalty"]
                        ranked_rating_earned = colors.get_rr_gradient(
                            rr_numeric_value, afk_penalty
                        )

                        player_level = player["PlayerIdentity"].get("AccountLevel")

                        if player["PlayerIdentity"]["Incognito"]:
                            Namecolor = colors.get_color_from_team(
                                player["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                agent=player["CharacterID"],
                                party_members=partyMembersList,
                            )
                        else:
                            Namecolor = colors.get_color_from_team(
                                player["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                party_members=partyMembersList,
                            )
                        if lastTeam != player["TeamID"]:
                            if lastTeamBoolean:
                                table.add_empty_row()
                        lastTeam = player["TeamID"]
                        lastTeamBoolean = True
                        if player["PlayerIdentity"]["HideAccountLevel"]:
                            if (
                                player["Subject"] == Requests.puuid
                                or player["Subject"] in partyMembersList
                                or hide_levels == False
                            ):
                                PLcolor = colors.level_to_color(player_level)
                            else:
                                PLcolor = ""
                        else:
                            PLcolor = colors.level_to_color(player_level)
                        # AGENT
                        # agent = str(agent_dict.get(player["CharacterID"].lower()))
                        agent = colors.get_agent_from_uuid(
                            player["CharacterID"].lower()
                        )
                        if agent == "" and len(Players) == 1:
                            isRange = True

                        # NAME
                        name = Namecolor

                        # VIEWS
                        # views = get_views(names[player["Subject"]])

                        # skin
                        skin = loadouts.get(player["Subject"], "")

                        # RANK
                        rankName = Ranks[playerRank["rank"]]
                        if cfg.get_feature_flag("aggregate_rank_rr") and cfg.table.get(
                            "rr"
                        ):
                            rankName += f" ({playerRank['rr']})"

                        # RANK RATING
                        rr = playerRank["rr"]

                        # short peak rank string
                        has_letter = any(
                            c.isalpha() for c in str(playerRank["peakrankep"])
                        )
                        peakRankAct = (
                            f" ({playerRank['peakrankep']}a{playerRank['peakrankact']})"
                            if has_letter
                            else f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                        )
                        if not cfg.get_feature_flag("peak_rank_act"):
                            peakRankAct = ""

                        # PEAK RANK
                        peakRank = Ranks[playerRank["peakrank"]] + peakRankAct

                        # PREVIOUS RANK
                        previousRank = Ranks[previousPlayerRank["rank"]]

                        # LEADERBOARD
                        leaderboard = playerRank["leaderboard"]

                        hs = colors.get_hs_gradient(hs)
                        wr = (
                            colors.get_wr_gradient(playerRank["wr"])
                            + f" ({playerRank['numberofgames']})"
                        )

                        if int(leaderboard) > 0:
                            is_leaderboard_needed = True

                        # LEVEL
                        level = PLcolor
                        table.add_row_table(
                            [
                                party_icon,
                                agent,
                                name,
                                # views,
                                skin,
                                rankName,
                                rr,
                                peakRank,
                                previousRank,
                                leaderboard,
                                hs,
                                wr,
                                kd,
                                level,
                                ranked_rating_earned,
                            ]
                        )

                        heartbeat_data["players"][player["Subject"]] = {
                            "puuid": player["Subject"],
                            "name": names[player["Subject"]],
                            "partyNumber": partyNum if party_icon != "" else 0,
                            "predictedParty": 0,  # premade thread'i sonradan doldurur
                            "agent": agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                            "rank": playerRank["rank"],
                            "peakRank": playerRank["peakrank"],
                            "peakRankAct": peakRankAct,
                            "peakRR": ppstats.get("peakRR") if isinstance(ppstats, dict) else None,
                            "rr": rr,
                            "kd": ppstats["kd"],
                            "headshotPercentage": ppstats["hs"],
                            "winPercentage": f"{playerRank['wr']} ({playerRank['numberofgames']})",
                            "level": player_level,
                            "agentImgLink": loadouts_data["Players"][
                                player["Subject"]
                            ].get("Agent", None),
                            # Authoritative team id (always present, incl. custom games)
                            "team": player["TeamID"],
                            "sprays": loadouts_data["Players"][player["Subject"]].get(
                                "Sprays", None
                            ),
                            "title": loadouts_data["Players"][player["Subject"]].get(
                                "Title", None
                            ),
                            "playerCard": player["PlayerIdentity"].get("PlayerCardID"),
                            "weapons": loadouts_data["Players"][player["Subject"]].get(
                                "Weapons", None
                            ),
                        }

                        stats.save_data(
                            {
                                player["Subject"]: {
                                    "name": names[player["Subject"]],
                                    "agent": agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                    "map": current_map,
                                    "rank": playerRank["rank"],
                                    "rr": rr,
                                    "match_id": coregame.match_id,
                                    "epoch": time.time(),
                                }
                            }
                        )
                        # bar()
            elif game_state == "PREGAME":
                already_played_with = []
                pregame_stats = pregame.get_pregame_stats()
                if pregame_stats == None:
                    continue
                server = pregame_stats.get("GamePodID", "")
                Players = pregame_stats["AllyTeam"]["Players"]
                presences.wait_for_presence(namesClass.get_players_puuid(Players))
                names = namesClass.get_names_from_puuids(Players)
                # Parallel cache warm-up so agent-select loads near-instantly.
                prefetch_player_data(Players, names)
                pregame_match_id = pregame_stats.get("ID")
                ensure_match_player_cache(pregame_match_id)
                # temporary until other regions gets fixed?
                # loadouts = loadoutsClass.get_match_loadouts(pregame.get_pregame_match_id(), pregame_stats, cfg.weapon, valoApiSkins, names,
                #   state="pregame")
                playersLoaded = 1
                with richConsole.status("Loading Players...") as status:
                    # with alive_bar(total=len(Players), title='Fetching Players', bar='classic2') as bar:
                    presence = presences.get_presence()
                    partyOBJ = menu.get_party_json(
                        namesClass.get_players_puuid(Players), presence
                    )
                    partyMembers = menu.get_party_members(Requests.puuid, presence)
                    partyMembersList = [a["Subject"] for a in partyMembers]
                    # log(f"retrieved names dict: {names}")
                    Players.sort(
                        key=lambda Players: Players["PlayerIdentity"].get(
                            "AccountLevel"
                        ),
                        reverse=True,
                    )
                    partyCount = 0
                    partyIcons = {}
                    for player in Players:
                        status.update(
                            f"Loading players... [{playersLoaded}/{len(Players)}]"
                        )
                        playersLoaded += 1
                        party_icon = ""
                        partyNum = 0

                        # set party premade icon
                        for party in partyOBJ:
                            if player["Subject"] in partyOBJ[party]:
                                if party not in partyIcons:
                                    partyIcons.update(
                                        {party: PARTYICONLIST[partyCount]}
                                    )
                                    # PARTY_ICON
                                    party_icon = PARTYICONLIST[partyCount]
                                    partyNum = partyCount + 1
                                    partyCount += 1
                                else:
                                    # PARTY_ICON
                                    party_icon = partyIcons[party]
                                    partyNum = PARTYICONLIST.index(party_icon) + 1
                        playerRank, previousPlayerRank, ppstats = get_or_fetch_rank_and_stats(
                            player["Subject"], pregame_match_id, names.get(player["Subject"])
                        )

                        if player["Subject"] == Requests.puuid:
                            if cfg.get_feature_flag("discord_rpc"):
                                rpc.set_data(
                                    {
                                        "rank": playerRank["rank"],
                                        "rank_name": colors.escape_ansi(
                                            NUMBERTORANKS[playerRank["rank"]]
                                        )
                                        + " | "
                                        + str(playerRank["rr"])
                                        + "rr",
                                    }
                                )
                        # rankStatus = playerRank[1]
                        # useless code since rate limit is handled in the requestsV
                        # while not rankStatus:
                        #     print("You have been rate limited, 😞 waiting 10 seconds!")
                        #     time.sleep(10)
                        #     playerRank = rank.get_rank(player["Subject"], seasonID)
                        #     rankStatus = playerRank[1]
                        # playerRank = playerRank[0]

                        hs = ppstats["hs"]
                        kd = ppstats["kd"]

                        rr_numeric_value = ppstats["RankedRatingEarned"]
                        afk_penalty = ppstats["AFKPenalty"]
                        ranked_rating_earned = colors.get_rr_gradient(
                            rr_numeric_value, afk_penalty
                        )

                        player_level = player["PlayerIdentity"].get("AccountLevel")
                        if player["PlayerIdentity"]["Incognito"]:
                            NameColor = colors.get_color_from_team(
                                pregame_stats["Teams"][0]["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                agent=player["CharacterID"],
                                party_members=partyMembersList,
                            )
                        else:
                            NameColor = colors.get_color_from_team(
                                pregame_stats["Teams"][0]["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                party_members=partyMembersList,
                            )

                        if player["PlayerIdentity"]["HideAccountLevel"]:
                            if (
                                player["Subject"] == Requests.puuid
                                or player["Subject"] in partyMembersList
                                or hide_levels == False
                            ):
                                PLcolor = colors.level_to_color(player_level)
                            else:
                                PLcolor = ""
                        else:
                            PLcolor = colors.level_to_color(player_level)
                        if player["CharacterSelectionState"] == "locked":
                            agent_color = color(
                                agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                fore=(255, 255, 255),
                            )
                        elif player["CharacterSelectionState"] == "selected":
                            agent_color = color(
                                agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                fore=(128, 128, 128),
                            )
                        else:
                            agent_color = color(
                                agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                fore=(54, 53, 51),
                            )

                        # AGENT
                        agent = agent_color

                        # NAME
                        name = NameColor

                        # VIEWS
                        # views = get_views(names[player["Subject"]])

                        # temporary until other regions gets fixed?
                        # skin
                        # skin = loadouts[player["Subject"]]

                        # RANK
                        rankName = Ranks[playerRank["rank"]]
                        if cfg.get_feature_flag("aggregate_rank_rr") and cfg.table.get(
                            "rr"
                        ):
                            rankName += f" ({playerRank['rr']})"

                        # RANK RATING
                        rr = playerRank["rr"]

                        # short peak rank string
                        has_letter = any(
                            c.isalpha() for c in str(playerRank["peakrankep"])
                        )
                        peakRankAct = (
                            f" ({playerRank['peakrankep']}a{playerRank['peakrankact']})"
                            if has_letter
                            else f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                        )
                        if not cfg.get_feature_flag("peak_rank_act"):
                            peakRankAct = ""
                        # PEAK RANK
                        peakRank = Ranks[playerRank["peakrank"]] + peakRankAct

                        # PREVIOUS RANK
                        previousRank = Ranks[previousPlayerRank["rank"]]

                        # LEADERBOARD
                        leaderboard = playerRank["leaderboard"]

                        hs = colors.get_hs_gradient(hs)
                        wr = (
                            colors.get_wr_gradient(playerRank["wr"])
                            + f" ({playerRank['numberofgames']})"
                        )

                        if int(leaderboard) > 0:
                            is_leaderboard_needed = True

                        # LEVEL
                        level = PLcolor

                        table.add_row_table(
                            [
                                party_icon,
                                agent,
                                name,
                                # views,
                                "",
                                rankName,
                                rr,
                                peakRank,
                                previousRank,
                                leaderboard,
                                hs,
                                wr,
                                kd,
                                level,
                                ranked_rating_earned,
                            ]
                        )

                        heartbeat_data["players"][player["Subject"]] = {
                            "name": names[player["Subject"]],
                            "partyNumber": partyNum if party_icon != "" else 0,
                            "agent": agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                            "team": pregame_stats["Teams"][0]["TeamID"],
                            "rank": playerRank["rank"],
                            "peakRank": playerRank["peakrank"],
                            "peakRankAct": peakRankAct,
                            "peakRR": ppstats.get("peakRR") if isinstance(ppstats, dict) else None,
                            "level": player_level,
                            "rr": rr,
                            "kd": ppstats["kd"],
                            "headshotPercentage": ppstats["hs"],
                            "winPercentage": f"{playerRank['wr']} ({playerRank['numberofgames']})",
                            "playerCard": player["PlayerIdentity"].get("PlayerCardID"),
                        }

                        # bar()
            if game_state == "MENUS":
                reset_match_player_cache()
                if hasattr(pstats, "clear_runtime_cache"):
                    pstats.clear_runtime_cache()

                server = ""
                already_played_with = []
                Players = menu.get_party_members(Requests.puuid, presence)
                names = namesClass.get_names_from_puuids(Players)
                # Parallel cache warm-up for party members.
                prefetch_player_data(Players, names)
                # Own loadout is available from the personalization endpoint while in menus.
                try:
                    self_weapons = loadoutsClass.get_self_loadout()
                except Exception:
                    self_weapons = None
                playersLoaded = 1
                with richConsole.status("Loading Players...") as status:
                    # with alive_bar(total=len(Players), title='Fetching Players', bar='classic2') as bar:
                    # log(f"retrieved names dict: {names}")
                    Players.sort(
                        key=lambda Players: Players["PlayerIdentity"].get(
                            "AccountLevel"
                        ),
                        reverse=True,
                    )
                    seen = []
                    for player in Players:

                        if player not in seen:
                            status.update(
                                f"Loading players... [{playersLoaded}/{len(Players)}]"
                            )
                            playersLoaded += 1
                            party_icon = PARTYICONLIST[0]
                            playerRank = rank.get_rank(player["Subject"], seasonID)
                            previousPlayerRank = rank.get_rank(
                                player["Subject"], previousSeasonID
                            )
                            if player["Subject"] == Requests.puuid:
                                if cfg.get_feature_flag("discord_rpc"):
                                    rpc.set_data(
                                        {
                                            "rank": playerRank["rank"],
                                            "rank_name": colors.escape_ansi(
                                                NUMBERTORANKS[playerRank["rank"]]
                                            )
                                            + " | "
                                            + str(playerRank["rr"])
                                            + "rr",
                                        }
                                    )

                            # rankStatus = playerRank[1]
                            # useless code since rate limit is handled in the requestsV
                            # while not rankStatus:
                            #     print("You have been rate limited, 😞 waiting 10 seconds!")
                            #     time.sleep(10)
                            #     playerRank = rank.get_rank(player["Subject"], seasonID)
                            #     rankStatus = playerRank[1]
                            # playerRank = playerRank["rank"]

                            ppstats = pstats.get_stats(player["Subject"], names.get(player["Subject"]))
                            hs = ppstats["hs"]
                            kd = ppstats["kd"]

                            rr_numeric_value = ppstats["RankedRatingEarned"]
                            afk_penalty = ppstats["AFKPenalty"]
                            ranked_rating_earned = colors.get_rr_gradient(
                                rr_numeric_value, afk_penalty
                            )

                            player_level = player["PlayerIdentity"].get("AccountLevel")
                            PLcolor = colors.level_to_color(player_level)

                            # AGENT
                            agent = ""

                            # NAME
                            name = color(names[player["Subject"]], fore=(76, 151, 237))

                            # RANK
                            rankName = Ranks[playerRank["rank"]]
                            if cfg.get_feature_flag(
                                "aggregate_rank_rr"
                            ) and cfg.table.get("rr"):
                                rankName += f" ({playerRank['rr']})"

                            # RANK RATING
                            rr = playerRank["rr"]

                            # short peak rank string
                            has_letter = any(
                                c.isalpha() for c in str(playerRank["peakrankep"])
                            )
                            peakRankAct = (
                                f" ({playerRank['peakrankep']}a{playerRank['peakrankact']})"
                                if has_letter
                                else f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                            )
                            if not cfg.get_feature_flag("peak_rank_act"):
                                peakRankAct = ""

                            # PEAK RANK
                            peakRank = (
                                Ranks[playerRank["peakrank"]] + peakRankAct
                            )

                            # PREVIOUS RANK
                            previousRank = Ranks[previousPlayerRank["rank"]]

                            # LEADERBOARD
                            leaderboard = playerRank["leaderboard"]

                            hs = colors.get_hs_gradient(hs)
                            wr = (
                                colors.get_wr_gradient(playerRank["wr"])
                                + f" ({playerRank['numberofgames']})"
                            )

                            if int(leaderboard) > 0:
                                is_leaderboard_needed = True

                            # LEVEL
                            level = PLcolor

                            table.add_row_table(
                                [
                                    party_icon,
                                    agent,
                                    name,
                                    "",
                                    rankName,
                                    rr,
                                    peakRank,
                                    previousRank,
                                    leaderboard,
                                    hs,
                                    wr,
                                    kd,
                                    level,
                                    ranked_rating_earned,
                                ]
                            )

                            heartbeat_data["players"][player["Subject"]] = {
                                "name": names[player["Subject"]],
                                "rank": playerRank["rank"],
                                "peakRank": playerRank["peakrank"],
                                "peakRankAct": peakRankAct,
                                "peakRR": ppstats.get("peakRR") if isinstance(ppstats, dict) else None,
                                "level": player_level,
                                "rr": rr,
                                "kd": ppstats["kd"],
                                "headshotPercentage": ppstats["hs"],
                                "winPercentage": f"{playerRank['wr']} ({playerRank['numberofgames']})",
                                "playerCard": player["PlayerIdentity"].get("PlayerCardID"),
                                "weapons": self_weapons if player["Subject"] == Requests.puuid else None,
                            }

                            # bar()
                    seen.append(player["Subject"])
            if (title := game_state_dict.get(game_state)) is None:
                # program_exit(1)
                time.sleep(9)
            
            title_parts = [f"VALORANT status: {title}"]

            if cfg.get_feature_flag("server_id") and server != "":
                parts = server.split('.')
                if len(parts) > 2:
                    short_serverID = '.'.join(parts[2:])
                else:
                    short_serverID = server
                title_parts.append(f" {colr('- ' + short_serverID, fore=(200, 200, 200))}")
            
            table.set_title(''.join(title_parts))
            
            if title is not None:
                if cfg.get_feature_flag("auto_hide_leaderboard") and (
                    not is_leaderboard_needed
                ):
                    table.set_runtime_col_flag("Pos.", False)

                if game_state == "MENUS":
                    table.set_runtime_col_flag("Party", False)
                    table.set_runtime_col_flag("Agent", False)
                    table.set_runtime_col_flag(cfg.weapon.capitalize(), False)

                if game_state == "INGAME":
                    if isRange:
                        table.set_runtime_col_flag("Party", False)
                        table.set_runtime_col_flag("Agent", False)

                # We don't to show the RR column if the "aggregate_rank_rr" feature flag is True.
                table.set_runtime_col_flag(
                    "RR",
                    cfg.table.get("rr")
                    and not cfg.get_feature_flag("aggregate_rank_rr"),
                )

                heartbeat_data["server"] = server_city(server)
                webserver.update(heartbeat_data)
                firstPrint = False

                # Gerçek premade tespitini (geçmiş maçların partyId'lerinden) arka
                # planda başlat; bitince predictedParty alanlarını doldurup paneli
                # yeniden push eder. İlk push'u bloklamaz.
                if game_state == "INGAME":
                    premades.update_for_match(
                        coregame_match_id,
                        namesClass.get_players_puuid(Players),
                        heartbeat_data,
                    )

                # print(f"VALORANT rank yoinker v{version}")
                if cfg.get_feature_flag("last_played"):
                    if len(already_played_with) > 0:
                        print("\n")
                        for played in already_played_with:
                            print(
                                f"Already played with {played['name']} (last {played['agent']}) {stats.convert_time(played['time_diff'])} ago. (Total played {played['times']} times)"
                            )
                already_played_with = []
        if cfg.cooldown == 0 and _has_console():
            input("Tekrar çekmek için enter'a basın...")
        else:
            # time.sleep(cfg.cooldown)
            pass
except KeyboardInterrupt:
    # lame implementation of fast ctrl+c exit
    os._exit(0)
except:
    log(traceback.format_exc())

    # Hata gerçekten bir hata mı, yoksa kullanıcı VALORANT'ı kapattığı için mi
    # oluştu? Oyun kapalıysa korkutucu hata yerine bilgilendirici uyarı göster.
    if not _is_valorant_running():
        info_message = (
            "VALORANT kapatıldı, bu yüzden Valorant Decloak da kapatıldı."
        )
        log("VALORANT kapatıldığı için program kapatılıyor")
        if _has_console():
            _set_console_visible(True)
            print(color(info_message, fore=(255, 255, 0)))
            input("çıkmak için enter'a basın...\n")
        else:
            _show_info_box(info_message)
        os._exit(0)

    error_message = (
        "Program bir hatayla karşılaştı. Sorun devam ederse"
        f" {os.getcwd()}\\logs klasöründeki kayıtlarla destek alın."
    )
    if _has_console():
        # Bring the console back so the error and prompt are visible
        _set_console_visible(True)
        print(color(error_message, fore=(255, 0, 0)))
        input("çıkmak için enter'a basın...\n")
    else:
        # Windowed build: no console, show the error in a message box instead
        _show_error_box(error_message)
    os._exit(1)