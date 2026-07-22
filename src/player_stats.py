import time
from urllib.parse import quote

import requests

TRACKER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://tracker.gg/",
}


class PlayerStats:
    STATS_TTL = 900  # cache successful season stats (seconds)
    FAIL_TTL = 120   # retry tracker sooner on failure (don't lock "Gizli" long)

    def __init__(self, Requests, log, config):
        self.Requests = Requests
        self.log = log
        self.config = config
        self.season_id = None    # set by main once the season is known
        self.stats_cache = {}    # puuid -> (result, timestamp)

    def clear_runtime_cache(self):
        """Kept for API compatibility; season stats are cached by TTL, not cleared here."""
        pass

    def _default_stats(self):
        return {
            "kd": "N/A",
            "hs": "N/A",
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "peakRR": None,
        }

    def _hidden_stats(self):
        # Shown when tracker.gg has no data / errors for this player
        return {
            "kd": "Gizli",
            "hs": "Gizli",
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "matchesCounted": 0,
            "peakRR": None,
            "source": "hidden",
        }

    def get_stats(self, puuid, name=None):
        # Serve from cache while not expired
        cached = self.stats_cache.get(puuid)
        if cached and time.time() < cached[1]:
            return cached[0]

        # Full-season aggregate straight from tracker.gg (one request).
        result = self._tracker_season_stats(name) if name else None
        ttl = self.STATS_TTL if result is not None else self.FAIL_TTL
        if result is None:
            result = self._hidden_stats()  # tracker error / no data => "Gizli"

        self.stats_cache[puuid] = (result, time.time() + ttl)
        return result

    def _tracker_season_stats(self, name):
        """Full current-season KD/HS from tracker.gg. Returns dict or None."""
        try:
            url = f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{quote(name)}"
            r = requests.get(url, headers=TRACKER_HEADERS, timeout=15)
            if r.status_code != 200:
                return None
            segments = r.json().get("data", {}).get("segments", [])
        except Exception as e:
            self.log(f"tracker.gg fetch error: {e}")
            return None

        best = None
        comp_segments = []
        for s in segments:
            if s.get("type") != "season":
                continue
            attrs = s.get("attributes", {})
            if attrs.get("playlist") != "competitive":
                continue
            comp_segments.append(s)
            if self.season_id and attrs.get("seasonId") == self.season_id:
                best = s
                break
            if best is None:
                best = s  # most recent competitive season as fallback

        if not best:
            return None

        st = best.get("stats", {})
        kd_val = st.get("kDRatio", {}).get("value")
        hs_val = st.get("headshotsPercentage", {}).get("value")
        matches = st.get("matchesPlayed", {}).get("value")
        # No usable numbers => treat as hidden
        if not isinstance(kd_val, (int, float)) and not isinstance(hs_val, (int, float)):
            return None
        return {
            "kd": round(kd_val, 2) if isinstance(kd_val, (int, float)) else "Gizli",
            "hs": round(hs_val) if isinstance(hs_val, (int, float)) else "Gizli",
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "matchesCounted": int(matches) if isinstance(matches, (int, float)) else 0,
            "peakRR": self._extract_peak_rr(comp_segments),
            "source": "tracker",
        }

    def _extract_peak_rr(self, comp_segments):
        """Peak RR from tracker.gg. The competitive season segment carries a
        `peakRank` stat whose `value` is the peak rating (e.g. 348). Take the
        highest across all competitive seasons."""
        best_rr = None
        for s in comp_segments:
            peak = (s.get("stats", {}) or {}).get("peakRank")
            if not isinstance(peak, dict):
                continue
            val = peak.get("value")
            if isinstance(val, (int, float)) and (best_rr is None or val > best_rr):
                best_rr = int(val)
        return best_rr


if __name__ == "__main__":
    from constants import version
    from requestsV import Requests
    from logs import Logging
    from errors import Error
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    Logging = Logging()
    log = Logging.log
    ErrorSRC = Error(log)
    Requests = Requests(version, log, ErrorSRC)

    player_stats = PlayerStats(Requests, log, "a")
    player_stats.season_id = None
    print(player_stats.get_stats("963ad672-61e1-537e-8449-06ece1a5ceb7", "tcoy#carti"))
