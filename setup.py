import sys
from cx_Freeze import setup, Executable
from src.constants import version

build_exe_options = {
    "path": sys.path,
    "include_files": [
        'config.json',          # ship config (henrik_api_key dahil)
        'web',                  # the local web panel (html/css/js)
        ('assets/Logo.ico', 'assets/Logo.ico'),  # kontrol penceresinin görev çubuğu simgesi
    ],
    "packages": [
        "requests", "colr", "InquirerPy", "websockets", "pypresence",
        "nest_asyncio", "rich", "websocket_server",
        # Paneli ayrı tarayıcı yerine gömülü native pencerede açmak için
        # (src/panel_window.py). Windows backend'i EdgeChromium/WebView2 olup
        # pythonnet (clr) ile çalışır; bu yüzden clr_loader/proxy_tools de
        # bundle'a girmeli, yoksa exe'de "No module named 'webview'/'clr'"
        # hatası verir. pywebview yüklenemezse panel_window varsayılan
        # tarayıcıya geri döndüğü için build yine de çalışır.
        "webview", "clr_loader", "proxy_tools",
    ],
    "excludes": ["test", "unittest", "pygments", "xmlrpc", "customtkinter"],
}

# Win32GUI base => no console window is created (only the GUI panel shows)
base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="ValorantDecloak",
    version=version,
    description='Valorant Decloak',
    executables=[
        Executable(
            "main.py",
            base=base,
            icon="./assets/Logo.ico",
            target_name="Decloak.exe",
        )
    ],
    options={"build_exe": build_exe_options},
)
