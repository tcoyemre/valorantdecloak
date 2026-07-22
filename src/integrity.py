"""Hafif bütünlük (self-integrity) kontrolü.

Lisans/güvenlik dosyalarının çalışma anında değiştirilip değiştirilmediğini
kontrol eder. Asıl anti-tamper koruması PyArmor (bkz. SECURITY.md) ile gelir;
bu modül ucuz bir ek kontroldür: kritik modüllerin beklenen SHA256'sını tutar
ve uyuşmazlıkta True/anomali bildirir.

Build alırken hash'leri güncellemek için:
    python -m src.integrity --print
çıktısını EXPECTED_HASHES'e yapıştır.
"""

import hashlib
import os
import sys

# Korunacak kritik dosyalar (src/ köküne göre).
_CRITICAL = [
    "names.py",
    "integrity.py",
]

# Build öncesi doldurulur. Boşsa kontrol "pas geçer" (uyarı verir).
EXPECTED_HASHES = {
    # "license_client.py": "abc123...",
}


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _src_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def compute_hashes() -> dict:
    out = {}
    base = _src_dir()
    for name in _CRITICAL:
        p = os.path.join(base, name)
        if os.path.exists(p):
            out[name] = _hash_file(p)
    return out


def verify() -> bool:
    """EXPECTED_HASHES doluysa eşleşmeyen dosya varsa False döner.

    Not: cx_Freeze ile kaynak .py yerine .pyc paketlenir; bu durumda kaynak
    hash'i uygulanmaz. O senaryoda anti-tamper için PyArmor'a güvenilir.
    """
    if not EXPECTED_HASHES:
        return True  # yapılandırılmamış -> bloklamadan geç
    current = compute_hashes()
    for name, expected in EXPECTED_HASHES.items():
        if current.get(name) != expected:
            return False
    return True


if __name__ == "__main__":
    if "--print" in sys.argv:
        for name, h in compute_hashes().items():
            print(f'    "{name}": "{h}",')
