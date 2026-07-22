import re
from concurrent.futures import ThreadPoolExecutor

import requests

# Gizli/streamer-mode isim çözümü için Henrik API anahtarı.
HENRIK_API_KEY = ""


class Names:

    def __init__(self, Requests, log, cfg=None):
        self.Requests = Requests
        self.log = log
        self.cfg = cfg
        # Gizli/streamer-mode isim çözümü tamamen yerelde yapılır.
        self._name_cache = {}

    def _build_name(self, player_data):
        if not player_data:
            return ""
        return f"{player_data.get('GameName', '')}#{player_data.get('TagLine', '')}"

    # --- Gizli/streamer-mode isim çözümü: yerelde Henrik API + vtl.lol fallback ---

    def _get_henrik_api_key(self):
        if HENRIK_API_KEY:
            return HENRIK_API_KEY
        return getattr(self.cfg, "henrikdev_api_key", "") or ""

    def _henrik_resolve(self, puuid):
        api_key = self._get_henrik_api_key()
        if not api_key:
            return None
        try:
            r = requests.get(
                f"https://api.henrikdev.xyz/valorant/v1/by-puuid/account/{puuid}",
                headers={"Authorization": api_key},
                timeout=10,
            )
            if r.status_code == 200:
                d = r.json().get("data", {})
                name, tag = d.get("name", ""), d.get("tag", "")
                if name:
                    return f"{name}#{tag}" if tag else name
        except Exception as e:
            self.log(f"henrik isim cozumu hatasi: {e}")
        return None

    def _vtl_resolve(self, puuid):
        try:
            r = requests.get(
                f"https://vtl.lol/id/{puuid}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=10,
            )
            if r.status_code == 200:
                m = re.search(
                    r'<div[^>]+class=["\'][^"\']*\bcard-title\b[^"\']*["\'][^>]*>([^<]+)</div>',
                    r.text, flags=re.IGNORECASE | re.DOTALL,
                )
                if m and m.group(1).strip():
                    return m.group(1).strip()
        except Exception as e:
            self.log(f"vtl isim cozumu hatasi: {e}")
        return None

    def _resolve_one(self, puuid):
        if puuid in self._name_cache:
            return self._name_cache[puuid]
        name = self._henrik_resolve(puuid) or self._vtl_resolve(puuid)
        if name:
            self._name_cache[puuid] = name
            return name
        return f"Gizli ({puuid[:8]})"

    def _resolve_hidden_names(self, puuids):
        """Birden çok gizli puuid'i yerelde çözer. Dönüş: {puuid: isim}."""
        if not puuids:
            return {}
        out = {}
        try:
            workers = min(10, len(puuids))
            with ThreadPoolExecutor(max_workers=workers) as ex:
                for puuid, name in zip(puuids, ex.map(self._resolve_one, puuids)):
                    out[puuid] = name
        except Exception as e:
            self.log(f"yerel isim cozumu hatasi: {e}")
            for puuid in puuids:
                out.setdefault(puuid, f"Gizli ({puuid[:8]})")
        return out

    def _resolve_hidden_name(self, puuid):
        return self._resolve_hidden_names([puuid]).get(puuid, f"Gizli ({puuid[:8]})")

    def get_name_from_puuid(self, puuid):
        try:
            response = requests.put(
                self.Requests.pd_url + "/name-service/v2/players",
                headers=self.Requests.get_headers(),
                json=[puuid],
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    name = self._build_name(data[0])
                    if name and name != "#":
                        return name
            return self._resolve_hidden_name(puuid)
        except Exception as e:
            self.log(f"Error fetching name from Riot API: {e}")
            return self._resolve_hidden_name(puuid)

    def get_multiple_names_from_puuid(self, puuids):
        try:
            response = requests.put(
                self.Requests.pd_url + "/name-service/v2/players",
                headers=self.Requests.get_headers(),
                json=puuids,
                verify=False,
                timeout=10
            )

            if response.status_code == 200:
                resp_data = response.json()
                if isinstance(resp_data, list):
                    # Riot returns entries in arbitrary order, so match each entry to its
                    # puuid via the "Subject" field instead of relying on list position.
                    by_subject = {
                        player.get("Subject"): player
                        for player in resp_data
                        if isinstance(player, dict) and player.get("Subject")
                    }
                    name_dict = {}
                    hidden = []
                    for puuid in puuids:
                        name = self._build_name(by_subject.get(puuid))
                        if name and name != "#":
                            name_dict[puuid] = name
                        else:
                            hidden.append(puuid)
                    # Gizli oyuncuların hepsini tek seferde yerelde çöz.
                    name_dict.update(self._resolve_hidden_names(hidden))
                    return name_dict
        except Exception as e:
            self.log(f"Error fetching names from Riot API: {e}")

        # Fallback: Riot yerel API yanıt vermezse hepsini yerelde çözmeyi dene.
        return self._resolve_hidden_names(puuids)

    def get_names_from_puuids(self, players):
        players_puuid = []
        for player in players:
            players_puuid.append(player["Subject"])
        return self.get_multiple_names_from_puuid(players_puuid)

    def get_players_puuid(self, Players):
        return [player["Subject"] for player in Players]
