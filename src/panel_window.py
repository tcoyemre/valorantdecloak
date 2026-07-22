"""Paneli ayrı bir tarayıcı sekmesi yerine kendi penceresinde (gömülü webview)
açar.

Neden ayrı süreç? pywebview, ``webview.start()`` çağrısının **mutlaka ana
thread'de** yapılmasını şart koşar (aksi halde "pywebview must be run on a main
thread" hatası verir). Ana uygulama ise kendi ana thread'ini sonsuz oyun
döngüsüyle meşgul ediyor. Bu yüzden paneli, tek işi pencereyi göstermek olan
küçük bir **çocuk süreçte** açarız; orada pywebview kendi ana thread'ine sahip
olur. Ana uygulama (main.py) hiç değişmez.

Çocuk süreç, ebeveynin PID'sini izler: ebeveyn (oyun) kapanınca pencereyi kendisi
kapatır; böylece ortada açık panel penceresi kalmaz. pywebview yoksa veya pencere
açılamazsa (ör. WebView2 yoksa) varsayılan tarayıcıya geri dönülür (fail-soft).

Yol 1: Yerel HTTP sunucusu (webserver.py) ve web/ dosyaları hiç değişmez; panel
sadece http://127.0.0.1:<port>/ adresini gösterir. LAN/telefon erişimi korunur.
"""

import importlib.util
import os
import subprocess
import sys
import threading
import webbrowser

CREATE_NO_WINDOW = 0x08000000  # çocuk süreçte konsol penceresi açma

# Çocuk sürecin (görüntüleyici) çıkış kodları, ebeveynin ne yapacağını belirler:
EXIT_USER_CLOSED = 0   # kullanıcı pencereyi kapattı -> programı kapat
EXIT_FALLBACK = 3      # webview açılamadı, tarayıcıya düşüldü -> programı KAPATMA

_lock = threading.Lock()
_proc = None       # aktif görüntüleyici çocuk süreç (varsa)
_closing = False   # close() ile biz mi kapatıyoruz (kullanıcı değil)


def _browser(url):
    """Varsayılan tarayıcıda aç (webview yoksa/başarısızsa son çare)."""
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def _viewer_cmd(url):
    """Kendi yürütülebilir dosyamızı `--panel-view` bayrağıyla yeniden başlatan
    komutu üretir. Donmuş (exe) ve kaynaktan çalışma için ayrı yollar."""
    parent = str(os.getpid())
    if getattr(sys, "frozen", False):
        return [sys.executable, "--panel-view", url, "--parent", parent]
    main_py = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
    )
    return [sys.executable, main_py, "--panel-view", url, "--parent", parent]


def open(url, title="Valorant Decloak", on_close=None, log=None):
    """Paneli webview penceresinde aç. Zaten açıksa yeni pencere açmaz. pywebview
    kullanılamıyorsa tarayıcıya düşer. Asla bloklamaz.

    on_close: kullanıcı panel penceresini kapatınca çağrılır (genelde
    programı kapatmak için os._exit). Tarayıcıya düşülen durumda ya da pencere
    biz close() ile kapatıldığında çağrılmaz."""
    global _proc, _closing
    with _lock:
        # Zaten açık bir panel penceresi varsa ikinciyi açma.
        if _proc is not None and _proc.poll() is None:
            return True

        # webview hiç kurulu değilse süreç başlatmaya gerek yok, tarayıcıya düş.
        if importlib.util.find_spec("webview") is None:
            if log:
                log("pywebview kurulu değil, panel tarayıcıda açılıyor")
            return _browser(url)

        try:
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = CREATE_NO_WINDOW
            _closing = False
            _proc = subprocess.Popen(_viewer_cmd(url), **kwargs)
            proc = _proc
        except Exception as e:
            if log:
                log(f"panel penceresi başlatılamadı, tarayıcıya dönülüyor: {e}")
            return _browser(url)

    # Ebeveyn tarafı izleyici: kullanıcı panel penceresini kapatınca (çocuk
    # süreç EXIT_USER_CLOSED ile biter) on_close'u çağır. Tarayıcıya düşme
    # (EXIT_FALLBACK) ya da bizim close()'umuz programı kapatmaz.
    if on_close is not None:
        def _await_close():
            try:
                code = proc.wait()
            except Exception:
                return
            with _lock:
                closing = _closing
            if not closing and code == EXIT_USER_CLOSED:
                if log:
                    log("panel penceresi kapatıldı, program kapatılıyor")
                on_close()

        threading.Thread(target=_await_close, daemon=True).start()
    return True


def close():
    """Açık panel penceresini (çocuk süreci) kapatır. Programdan çıkarken çağır.
    Bu kapanış on_close geri çağrımını TETİKLEMEZ (kullanıcı değil biz kapattık)."""
    global _proc, _closing
    with _lock:
        _closing = True
        if _proc is not None and _proc.poll() is None:
            try:
                _proc.terminate()
            except Exception:
                pass
        _proc = None


# ----------------------------------------------------------------------------
# Çocuk süreç tarafı: gerçek pencereyi açan kod (ana thread'de çalışır).
# main.py, --panel-view bayrağını görünce run_viewer'ı çağırıp çıkar.
# ----------------------------------------------------------------------------

def _pid_alive(pid):
    """Verilen PID'li süreç hâlâ çalışıyor mu? (Windows)"""
    if not pid:
        return True
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        h = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid)
        )
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return bool(ok) and code.value == STILL_ACTIVE
    except Exception:
        # PID kontrolü yapılamazsa pencereyi açık tut (yanlışlıkla kapatma).
        return True


def run_viewer(url, parent_pid=None, title="Valorant Decloak"):
    """Çocuk sürecin ana thread'inde çağrılır: paneli native pencerede gösterir,
    bloklar. Ebeveyn süreç ölünce pencereyi kapatır. webview açılamazsa
    tarayıcıya düşer.

    Dönüş: ebeveynin yorumladığı çıkış kodu. EXIT_USER_CLOSED (0) kullanıcı
    pencereyi kapattı demektir; EXIT_FALLBACK (3) webview açılamadı, tarayıcıya
    düşüldü demektir (ebeveyn bu durumda kapanmamalı)."""
    try:
        import webview
    except Exception:
        _browser(url)
        return EXIT_FALLBACK

    try:
        window = webview.create_window(
            title,
            url=url,
            width=1100,
            height=720,
            min_size=(820, 560),
        )

        # Not: webview.start()'a icon parametresi VERİLMİYOR. Verildiğinde bu
        # pywebview/EdgeChromium sürümünde pencere kapatma (window.destroy())
        # GUI döngüsünü durdurmuyor ve süreç asılı kalıyor. Donmuş exe zaten
        # kendi .ico'sunu taşıdığı için pencere simgesi yine de doğru görünür.
        if parent_pid:
            def _watch():
                import time

                while True:
                    time.sleep(1.0)
                    if not _pid_alive(parent_pid):
                        # Ebeveyn (oyun) kapandı: bu görüntüleyici sürecin tek
                        # işi pencereyi göstermek olduğundan onu doğrudan
                        # sonlandır. (Thread'ler arası window.destroy() bu
                        # pywebview sürümünde kararsız çalışıyor; os._exit
                        # garantili ve pencereyi anında kapatır.)
                        os._exit(0)

            threading.Thread(target=_watch, daemon=True).start()

        webview.start()  # kullanıcı pencereyi kapatana kadar bloklar
        return EXIT_USER_CLOSED
    except Exception:
        # Pencere hiç açılamadıysa (ör. WebView2 runtime yok) tarayıcıya düş.
        _browser(url)
        return EXIT_FALLBACK
