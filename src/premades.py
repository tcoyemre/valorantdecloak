import json
import os
import threading
import time


class Premades:
    """Gerçek premade (parti) tespiti — geçmiş maçların partyId'lerinden.

    Riot, CANLI maç verisinde (core-game) parti bilgisini gizler; presence ise
    yalnızca senin arkadaşlarını gösterir. Ama TAMAMLANMIŞ maç detayları
    (`/match-details/v1/matches/{id}`, pd sunucusu) her oyuncu için gerçek
    `partyId` taşır. tracker.gg'nin "kimler birlikte queue atmış" göstergesi de
    tam olarak bunu kullanır: iki oyuncu geçmiş bir maçta aynı partideyse, şu an
    da birlikte olma olasılıkları yüksektir.

    Yöntem (her oyuncu için son `depth` maç taranır):
      1. /match-history/v1/history/{puuid}  -> son maç kimlikleri
      2. /match-details/v1/matches/{id}     -> {puuid: partyId}
      3. Mevcut maçtaki oyunculardan, geçmiş bir maçta aynı partyId'yi paylaşanlar
         birleştirilir (union-find) -> grup numaraları.

    İstek yoğun olduğu için:
      - Maç detayları DEĞİŞMEZ -> kalıcı disk cache (oturumlar arası yeniden
        kullanılır; zamanla çağrı sayısı çok azalır).
      - Hesaplama arka planda (daemon thread) yapılır; bitince predictedParty
        alanları doldurulup panel `webserver.update()` ile yeniden push edilir.
        (Tarayıcı /data'yı zaten saniyede bir poll'lediği için sonuç anında
        görünür; ana döngü bloklanmaz.)
    """

    HISTORY_TTL = 600          # oyuncu maç-listesi cache süresi (sn)
    DISK_CACHE_MAX = 1500      # diske yazılan maç detay sayısı tavanı

    def __init__(self, Requests, log, webserver, depth=3):
        self.Requests = Requests
        self.log = log
        self.webserver = webserver
        self.depth = depth

        self._lock = threading.Lock()
        self._history_cache = {}   # puuid -> (match_ids, ts)
        self._party_maps = {}      # match_id -> {puuid: partyId}  (değişmez)
        self._results = {}         # match_id -> {puuid: grup_no}
        self._inflight = set()     # hesaplaması süren match_id'ler
        self._current_match = None

        self._cache_path = os.path.join(
            os.getenv("APPDATA") or ".", "decloak", "premade_cache.json"
        )
        self._load_disk_cache()

    # ---------------- genel API ----------------

    def update_for_match(self, match_id, puuids, heartbeat_data):
        """Bu maç için premade gruplarını hazırla. Sonuç cache'de varsa hemen
        uygula; yoksa arka planda hesapla ve bitince paneli yeniden push et."""
        if not match_id or not puuids:
            return
        self._current_match = match_id

        with self._lock:
            cached = self._results.get(match_id)
            already_running = match_id in self._inflight
            if cached is None and not already_running:
                self._inflight.add(match_id)
                start = True
            else:
                start = False

        if cached is not None:
            self._apply(cached, heartbeat_data)
            return

        if start:
            t = threading.Thread(
                target=self._worker,
                args=(match_id, list(puuids), heartbeat_data),
                daemon=True,
            )
            t.start()

    # ---------------- arka plan ----------------

    def _worker(self, match_id, puuids, heartbeat_data):
        try:
            groups = self._compute(match_id, puuids)
        except Exception as e:
            self.log(f"premade hesaplama hatası: {e}")
            groups = {}
        finally:
            with self._lock:
                self._inflight.discard(match_id)

        with self._lock:
            self._results[match_id] = groups
        self._save_disk_cache()

        # Maç değiştiyse eski sonucu push etme.
        if self._current_match != match_id:
            return
        self._apply(groups, heartbeat_data)
        try:
            self.webserver.update(heartbeat_data)
            self.log(f"premade grupları güncellendi: {groups}")
        except Exception as e:
            self.log(f"premade push hatası: {e}")

    def _apply(self, groups, heartbeat_data):
        players = heartbeat_data.get("players", {})
        for puuid, p in players.items():
            if isinstance(p, dict):
                p["predictedParty"] = groups.get(puuid, 0)

    def _compute(self, current_match_id, puuids):
        puuid_set = set(puuids)

        # Taranacak benzersiz geçmiş maçları topla (oyuncular arası örtüşme
        # sayesinde gerçek benzersiz sayı genelde çok daha azdır).
        match_ids = set()
        for puuid in puuids:
            for mid in self._get_history(puuid):
                if mid and mid != current_match_id:
                    match_ids.add(mid)

        # union-find
        parent = {p: p for p in puuids}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for mid in match_ids:
            party_map = self._get_party_map(mid)
            if not party_map:
                continue
            # Bu geçmiş maçta, mevcut maçtaki oyuncuları partyId'ye göre grupla.
            by_party = {}
            for puuid in puuids:
                pid = party_map.get(puuid)
                if pid:
                    by_party.setdefault(pid, []).append(puuid)
            for members in by_party.values():
                if len(members) >= 2:
                    for other in members[1:]:
                        union(members[0], other)

        # Bileşenleri (>=2 üyeli) numaralandır.
        comps = {}
        for p in puuids:
            comps.setdefault(find(p), []).append(p)

        result = {}
        num = 0
        for members in comps.values():
            if len(members) >= 2:
                num += 1
                for m in members:
                    result[m] = num
        return result

    # ---------------- pd API yardımcıları ----------------

    @staticmethod
    def _as_json(resp):
        """pd fetch ham Response döndürür; güvenle json'a çevir."""
        if resp is None:
            return None
        if isinstance(resp, dict):
            return resp
        try:
            if getattr(resp, "status_code", 200) != 200:
                return None
            return resp.json()
        except Exception:
            return None

    def _get_history(self, puuid):
        now = time.time()
        with self._lock:
            cached = self._history_cache.get(puuid)
        if cached and now < cached[1]:
            return cached[0]

        endpoint = (
            f"/match-history/v1/history/{puuid}"
            f"?startIndex=0&endIndex={self.depth}"
        )
        data = self._as_json(
            self.Requests.fetch(url_type="pd", endpoint=endpoint, method="get")
        )
        ids = []
        if isinstance(data, dict):
            for h in data.get("History", []) or []:
                mid = h.get("MatchID") if isinstance(h, dict) else None
                if mid:
                    ids.append(mid)
        ids = ids[: self.depth]

        with self._lock:
            self._history_cache[puuid] = (ids, now + self.HISTORY_TTL)
        return ids

    def _get_party_map(self, match_id):
        with self._lock:
            cached = self._party_maps.get(match_id)
        if cached is not None:
            return cached

        endpoint = f"/match-details/v1/matches/{match_id}"
        data = self._as_json(
            self.Requests.fetch(url_type="pd", endpoint=endpoint, method="get")
        )
        party_map = {}
        if isinstance(data, dict):
            for p in data.get("players", []) or []:
                if not isinstance(p, dict):
                    continue
                subject = p.get("subject") or p.get("Subject")
                party_id = p.get("partyId") or p.get("PartyID")
                if subject and party_id:
                    party_map[subject] = party_id

        with self._lock:
            self._party_maps[match_id] = party_map
        return party_map

    # ---------------- disk cache ----------------

    def _load_disk_cache(self):
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # Yalnızca {match_id: {puuid: partyId}} biçimini kabul et.
                self._party_maps = {
                    k: v for k, v in data.items() if isinstance(v, dict)
                }
                self.log(
                    f"premade cache yüklendi: {len(self._party_maps)} maç"
                )
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self._party_maps = {}

    def _save_disk_cache(self):
        try:
            with self._lock:
                items = list(self._party_maps.items())
            # Tavanı aşarsa en eskileri at (ekleme sırası korunur).
            if len(items) > self.DISK_CACHE_MAX:
                items = items[-self.DISK_CACHE_MAX:]
            os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
            tmp = self._cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dict(items), f)
            os.replace(tmp, self._cache_path)
        except OSError as e:
            self.log(f"premade cache yazılamadı: {e}")
