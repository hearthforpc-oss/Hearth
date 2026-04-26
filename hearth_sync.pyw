# Hearth v1.6
# Copyright 2026 Hearth Software. All rights reserved.
# Unauthorized copying, distribution, or modification is prohibited.
# Built by Chester Houston. hearthforpc@gmail.com

#
#
# ## Architecture
# 
# ### How it works
# 1. Player A shares a world — Hearth pushes save files to a shared Google Drive folder
# 2. Player B opens Hearth — it pulls Player A's world into a free local save slot
# 3. Player B plays solo, closes game — Hearth pushes the session back to Drive under Player A's folder
# 4. Player A pulls their world back with Player B's progress
# 
# ### Google Drive requirement
# - Must use **Mirror Files** mode, NOT Stream Files
# - Shared folder structure: `[Drive]/[Game]/[Owner]/[WorldID]/`
# 
# ### Supported games
# - Icarus (Steam ID required)
# - Valheim (paired .db + .fwl files)
# - Terraria
# - Terraria (tModLoader) — cannot launch directly from Steam when modded, launch_cmd = None
# - Core Keeper (numeric slots, Steam ID required, Steam Cloud must be off)
# - Enshrouded (hex slots, Steam Cloud must be off)
# - Sons of the Forest (unverified)
# - Custom Game
# 
# ---
# 
# ## Key Files in Drive Folder (per world)
# - `meta.json` — owner, world ID, display name, timestamp
# - `worldmap.json` — maps each player's username to their local slot
# - `hearth.lock` — written when a player is actively hosting, cleared on game close
# - `hearth.log` — activity log written by all players
# 
# ---
# 
# ## Enshrouded Save System (critical knowledge)
# 
# ### How Enshrouded saves work
# - Saves live in `%USERPROFILE%\Saved Games\Enshrouded\`
# - Each world slot is identified by a hex ID (not a readable name)
# - Slot 0 = `3ad85aea`, Slot 1 = `3bd85c7d`, Slot 2 = `38d857c4`, etc.
# - Full hex slot map is in `ENSHROUDED_SLOTS` dict in the code
# 
# ### Files per world slot (ALL required)
# For hex ID `3ad85aea`:
# - `3ad85aea` — main save file (required)
# - `3ad85aea-1` — backup of main save (required to push/pull)
# - `3ad85aea_info` — world info
# - `3ad85aea_info-1` — backup of world info
# - `3ad85aea-index` — tells game which version to load (`"latest": N`)
# - `3ad85aea_info-index` — same for info file
# - `3ad85aea-index` and `3ad85aea_info-index` must have `"latest": 0` when transferred to a new slot, otherwise Enshrouded looks for a numbered backup that doesn't exist and won't show the world
# 
# ### Steam Cloud conflict
# - Enshrouded uses Steam Cloud by default
# - If enabled, saves go to Steam's servers not the local folder
# - Hearth cannot see Steam Cloud saves
# - Fix: Steam → right-click Enshrouded → Properties → General → uncheck Steam Cloud
# - Hearth now shows a warning in the worlds list when no local save folder is detected for Steam Cloud games
# 
# ### Slot remapping (worldmap system)
# When Player B pulls Player A's world:
# 1. Player A's hex (e.g. `3ad85aea`) is the "remote_hex"
# 2. Hearth finds Player B's first free slot (e.g. `3bd85c7d`) = "local_hex"
# 3. All files are copied and renamed from `3ad85aea*` to `3bd85c7d*`
# 4. Index files are patched: `"latest": 0` in both `-index` files
# 5. `worldmap.json` in Drive is updated: `{"Sour Nipples": {"local_hex": "3bd85c7d"}}`
# 
# When Player B pushes back after playing:
# 1. `_push_enshrouded` reads its local hex (`3bd85c7d`)
# 2. Scans all Drive worldmaps to find which remote folder this local hex belongs to
# 3. Finds `worldmap.json` in `Drive/Enshrouded/Chester/3ad85aea` with `{"Sour Nipples": {"local_hex": "3bd85c7d"}}`
# 4. Renames files back to `3ad85aea*` and pushes to `Drive/Enshrouded/Chester/3ad85aea`
# 
# ---
# 
# ## Code Architecture — Push/Pull
# 
# ### Dispatcher pattern (added in 0.9.4)
# Instead of one giant push_world/pull_world with branching logic, each game has dedicated functions:
# 
# ```
# _push_enshrouded()   _pull_enshrouded()
# _push_core_keeper()  _pull_core_keeper()
# _push_standard()     _pull_standard()
# 
# push_world() — dispatcher
# pull_world() — dispatcher
# ```
# 
# `push_world` and `pull_world` are kept as the public interface so nothing else in the app needs to change.
# 
# ### _push_standard (Icarus, Valheim, Terraria, etc.)
# - Validates world_id before calling get_drive_world_folder (prevents None folder creation)
# - Copies main save file + paired file if exists (e.g. Valheim .fwl)
# 
# ### _pull_standard
# - Validates world_id is not empty or "None" before proceeding
# - Filters by game's save_ext — only copies matching file types, prevents foreign files from being pulled down
# 
# ### _push_enshrouded
# - Worldmap-aware: checks if local_hex belongs to someone else's world via worldmap scan
# - If so, renames files back to remote_hex and pushes to owner's Drive folder
# 
# ### _pull_enshrouded
# - Reads worldmap, finds or assigns a free local slot
# - Copies and renames all files from remote_hex to local_hex
# - Patches both index files to "latest": 0
# 
# =============================================================================

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import json, os, shutil, time, threading, subprocess, sys, hashlib
import urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
import ctypes
if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("hearthforpc.hearth.1.6")

def _resource_path(relative):
    """Get absolute path to resource — works for script and PyInstaller exe."""
    import sys
    base = getattr(sys, '_MEIPASS', Path(__file__).parent)
    return Path(base) / relative

# ── Dependencies ──────────────────────────────────────────────────────────────
try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False

try:
    import win32gui
    HAVE_WIN32 = True
except ImportError:
    HAVE_WIN32 = False

try:
    from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem as TrayItem
    from PIL import Image as PILImage
    HAVE_TRAY = True
except ImportError:
    HAVE_TRAY = False

VERSION   = "1.6"
COPYRIGHT = "Copyright 2026 Hearth Software. All rights reserved."
SUPPORT   = "hearthforpc@gmail.com"
DONATE    = "https://buymeacoffee.com/hearthapp"
GITHUB_REPO     = "hearthforpc-oss/Hearth"
GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases/latest"
GITHUB_API      = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CERT_GOAL       = 200.0   # certificate cost in dollars
CERT_GIST_URL   = "https://gist.githubusercontent.com/hearthforpc-oss/raw/hearth_fund.json"

# ── Known save locations to scan for auto-detect ──────────────────────────────
SCAN_ROOTS = [
    Path.home() / "Documents" / "My Games",
    Path.home() / "Documents" / "SavedGames",
    Path.home() / "Saved Games",
    Path(os.environ.get("APPDATA","")) / ".." / "LocalLow",
    Path(os.environ.get("APPDATA","")) / ".." / "Local",
    Path(os.environ.get("APPDATA","")) ,
]
GAME_SAVE_EXTENSIONS = {".sav",".save",".wld",".db",".fwl",".world",".map",".dat",".json",".savegame",".world.gzip"}
# Extensions too generic to trust alone — only count if folder looks like a game
GENERIC_EXTENSIONS  = {".dat",".json"}

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_FILE   = Path.home() / ".hearth_config.json"
LOCK_FILENAME   = "hearth.lock"
META_FILENAME   = "meta.json"
MAP_FILENAME    = "worldmap.json"
LOG_FILENAME    = "hearth.log"
STATUS_FILENAME = "hearth_status.json"
MAX_BACKUPS     = 10
BACKUP_FOLDER = Path.home() / "Hearth_Backups"
ICON_PATH        = Path(__file__).parent / "hearth_flame_cropped.png"
ICO_PATH         = _resource_path("hearth.ico")
TRAY_ORANGE_PATH = _resource_path("tray_orange.png")
TRAY_BLUE_PATH   = _resource_path("tray_blue.png")
TRAY_GREEN_PATH  = _resource_path("tray_green.png")
TRAY_RED_PATH    = _resource_path("tray_red.png")

# ── Colors ────────────────────────────────────────────────────────────────────
C = {
    "bg":      "#0d0f18", "surface": "#151825", "card":   "#1c1f2e",
    "card2":   "#232638", "border":  "#2a2d3e", "accent": "#e8622a",
    "accent2": "#c44d1a", "blue":    "#1e3a5f", "blue2":  "#2a4f80",
    "text":    "#eaeaea", "muted":   "#6b7280", "green":  "#22c55e",
    "amber":   "#f59e0b", "sky":     "#60a5fa", "red":    "#ef4444",
}

# ── Enshrouded hex slot map ───────────────────────────────────────────────────
ENSHROUDED_SLOTS = {
    0:"3ad85aea",1:"3bd85c7d",2:"38d857c4",3:"39d85957",
    4:"36d8549e",5:"37d85631",6:"34d85178",7:"35d8530b",
    8:"32d84e52",9:"33d84fe5",
}
ENSHROUDED_HEX_TO_SLOT = {v:k for k,v in ENSHROUDED_SLOTS.items()}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _docs():
    od = Path(os.environ.get("USERPROFILE","")) / "OneDrive" / "Documents"
    st = Path(os.environ.get("USERPROFILE","")) / "Documents"
    return od if od.exists() else st

def _steam_id32(sid64):
    try: return str(int(sid64) - 76561197960265728)
    except: return ""

def ts():     return datetime.now().strftime("%H:%M:%S")
def ts_full():return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ── Games ─────────────────────────────────────────────────────────────────────
GAMES = {
    "Icarus": {
        "process":"Icarus","exclude":["icarusmodmanager"],
        "save_paths":lambda cfg:[Path(os.environ["LOCALAPPDATA"])/"Icarus"/"Saved"/"PlayerData"/cfg.get("steam_id","")/"Prospects"],
        "save_ext":".json","backup_pattern":"_backup_","needs_steam_id":True,
        "launch_cmd":"steam://rungameid/1149460","steam_cloud":False,
        "slot_based":False,"paired_ext":None,
    },
    "Valheim": {
        "process":"valheim","exclude":[],
        "save_paths":lambda cfg:[
            Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"IronGate"/"Valheim"/"worlds_local",
            Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"IronGate"/"Valheim"/"worlds",
            Path(os.environ.get("PROGRAMFILES(X86)",os.environ.get("PROGRAMFILES","C:/Program Files (x86)")))/"Steam"/"userdata"/_steam_id32(cfg.get("steam_id",""))/str(892970)/"remote"/"worlds",
            Path(os.environ.get("USERPROFILE",""))/"AppData"/"Local"/"Programs"/"Steam"/"userdata"/_steam_id32(cfg.get("steam_id",""))/str(892970)/"remote"/"worlds",
        ],
        "save_ext":".fwl","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/892970","steam_cloud":False,
        "slot_based":False,"paired_ext":".db",
    },
    "Terraria": {
        "process":"Terraria","exclude":[],
        "save_paths":lambda cfg:[
            _docs()/"My Games"/"Terraria"/"Worlds",
            Path(os.environ.get("USERPROFILE",""))/"Documents"/"My Games"/"Terraria"/"Worlds",
        ],
        "save_ext":".wld","backup_pattern":".bak","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/105600","steam_cloud":False,
        "slot_based":False,"paired_ext":None,
    },
    "Terraria (tModLoader)": {
        "process":None,"exclude":[],"window_title":"Terraria",
        "save_paths":lambda cfg:[
            _docs()/"My Games"/"Terraria"/"tModLoader"/"Worlds",
            Path(os.environ.get("USERPROFILE",""))/"Documents"/"My Games"/"Terraria"/"tModLoader"/"Worlds",
        ],
        "save_ext":".wld","backup_pattern":".bak","needs_steam_id":False,
        "launch_cmd":None,"launch_note":"Launch through tModLoader — cannot launch directly from Steam when modded.",
        "steam_cloud":False,"slot_based":False,"paired_ext":None,
    },
    "Core Keeper": {
        "process":"CoreKeeper","exclude":[],
        "save_paths":lambda cfg:[
            Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"Pugstorm"/"Core Keeper"/"Steam"/cfg.get("steam_id","")/"worlds",
            Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"Pugstorm"/"Core Keeper"/"Steam"/_steam_id32(cfg.get("steam_id",""))/"worlds",
        ],
        "info_paths":lambda cfg:[
            Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"Pugstorm"/"Core Keeper"/"Steam"/cfg.get("steam_id","")/"worldinfos",
            Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"Pugstorm"/"Core Keeper"/"Steam"/_steam_id32(cfg.get("steam_id",""))/"worldinfos",
        ],
        "save_ext":".world.gzip","backup_pattern":".backup","needs_steam_id":True,
        "launch_cmd":"steam://rungameid/1621690",
        "steam_cloud":True,"steam_cloud_note":"Core Keeper uses Steam Cloud by default. Disable it in Steam → Core Keeper → Properties → General.",
        "slot_based":True,"slot_type":"numeric","paired_ext":None,
    },
    "Enshrouded": {
        "process":"enshrouded","exclude":[],
        "save_paths":lambda cfg:[Path(os.environ.get("USERPROFILE",""))/"Saved Games"/"Enshrouded"],
        "save_ext":"","backup_pattern":"_info-1","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/1203620",
        "steam_cloud":True,"steam_cloud_note":"Enshrouded uses Steam Cloud by default. Disable it in Steam → Enshrouded → Properties → General.",
        "slot_based":True,"slot_type":"hex","paired_ext":None,
    },
    "Sons of the Forest": {
        "process":"SonsOfTheForest","exclude":[],
        "save_paths":lambda cfg:[Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"Endnight"/"SonsOfTheForest"/"Saves"],
        "save_ext":".json","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/1326470","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "7 Days to Die": {
        "process":"7DaysToDie","exclude":[],
        "save_paths":lambda cfg:[Path(os.environ.get("APPDATA",""))/"7DaysToDie"/"Saves"],
        "save_ext":"","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/251570","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "The Forest": {
        "process":"TheForest","exclude":[],
        "save_paths":lambda cfg:[Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"SKS"/"TheForest"],
        "save_ext":".sav","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/242760","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "Grounded": {
        "process":"Maine","exclude":[],
        "save_paths":lambda cfg:[Path(os.environ.get("USERPROFILE",""))/"Saved Games"/"Grounded"],
        "save_ext":".sav","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/962130","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "Astroneer": {
        "process":"Astro","exclude":[],
        "save_paths":lambda cfg:[Path(os.environ.get("LOCALAPPDATA",""))/"Astro"/"Saved"/"SaveGames"],
        "save_ext":".savegame","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/361420","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "V Rising": {
        "process":"VRising","exclude":["vrisingserver"],
        "save_paths":lambda cfg:[Path(os.environ.get("APPDATA",""))/".."/"LocalLow"/"Stunlock Studios"/"VRising"/"Saves"/"v3"],
        "save_ext":".save","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/1604030","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "Don't Starve Together": {
        "process":"dontstarve_steam","exclude":[],
        "save_paths":lambda cfg:[
            Path(os.environ.get("USERPROFILE",""))/"Documents"/"Klei"/"DoNotStarveTogether"/cfg.get("steam_id","")/"client_save",
            Path(os.environ.get("USERPROFILE",""))/"Documents"/"Klei"/"DoNotStarveTogether"/_steam_id32(cfg.get("steam_id",""))/"client_save",
        ],
        "save_ext":"","backup_pattern":"_backup","needs_steam_id":True,
        "launch_cmd":"steam://rungameid/322330","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "Stardew Valley": {
        "process":"StardewValley","exclude":[],
        "save_paths":lambda cfg:[Path(os.environ.get("APPDATA",""))/"StardewValley"/"Saves"],
        "save_ext":"","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/413150","steam_cloud":False,
        "slot_based":False,"paired_ext":None,"verified":False,
    },
    "Custom Game": {
        "process":None,"exclude":[],
        "save_paths":lambda cfg:[Path(cfg.get("custom_save_path",""))] if cfg.get("custom_save_path") else [],
        "save_ext":"","backup_pattern":"_backup","needs_steam_id":False,
        "launch_cmd":None,"steam_cloud":False,"slot_based":False,"paired_ext":None,
    },
}

# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f: return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=2)

def is_first_run(cfg):
    return not cfg.get("username") or not cfg.get("drive_folder")

# ── Process detection ─────────────────────────────────────────────────────────
def is_window_open(title_prefix):
    if not HAVE_WIN32: return False
    found=[]
    def cb(hwnd,_):
        t=win32gui.GetWindowText(hwnd)
        if t.startswith(title_prefix): found.append(t)
    try: win32gui.EnumWindows(cb,None)
    except: pass
    return len(found)>0

def is_game_running(game_key):
    info=GAMES.get(game_key,{})
    win_title=info.get("window_title")
    if win_title: return is_window_open(win_title)
    process=info.get("process")
    if not process: return False
    pl=process.lower()
    excl=[e.lower() for e in info.get("exclude",[])]
    if HAVE_PSUTIL:
        try:
            for p in psutil.process_iter(["name"]):
                n=(p.info["name"] or "").lower()
                if n.startswith(pl) and n.replace(".exe","") not in excl: return True
        except: pass
        return False
    try:
        si=subprocess.STARTUPINFO()
        si.dwFlags|=subprocess.STARTF_USESHOWWINDOW; si.wShowWindow=0
        r=subprocess.run(["tasklist"],capture_output=True,text=True,startupinfo=si)
        for line in r.stdout.lower().splitlines():
            pts=line.strip().split()
            if pts and pts[0].replace(".exe","").startswith(pl) and pts[0].replace(".exe","") not in excl: return True
    except: pass
    return False

def any_game_running():
    for gk in GAMES:
        if is_game_running(gk): return gk
    return None

# ── Save path helpers ─────────────────────────────────────────────────────────
def find_save_folder(game_key,cfg):
    info=GAMES.get(game_key,{})
    custom=cfg.get("custom_paths",{}).get(game_key,"")
    if custom and Path(custom).exists(): return Path(custom)
    for p in info.get("save_paths",lambda c:[])(cfg):
        try:
            pp=Path(str(p))
            if pp.exists(): return pp
            rp=pp.resolve()
            if rp.exists(): return rp
        except: pass
    return None

def find_info_folder(game_key,cfg):
    info=GAMES.get(game_key,{})
    for p in info.get("info_paths",lambda c:[])(cfg):
        try:
            pp=Path(str(p)).resolve()
            if pp.exists(): return pp
        except: pass
    return None

def get_ck_world_name(game_key,cfg,slot_num):
    inf=find_info_folder(game_key,cfg)
    if not inf: return f"World {slot_num+1}"
    wf=inf/f"{slot_num}.worldinfo"
    if not wf.exists(): return f"World {slot_num+1}"
    try:
        with open(wf,"r",encoding="utf-8",errors="ignore") as f:
            d=json.load(f); n=d.get("name","").strip()
            return n if n else f"World {slot_num+1}"
    except: return f"World {slot_num+1}"

def get_slot_worlds(game_key,cfg):
    info=GAMES.get(game_key,{}); slot_type=info.get("slot_type","numeric")
    folder=find_save_folder(game_key,cfg)
    if not folder: return []
    results=[]
    if slot_type=="numeric":
        ext=info.get("save_ext",".world.gzip"); backup=info.get("backup_pattern",".backup")
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.name.endswith(ext) and backup not in f.name:
                try:
                    sn=int(f.name.split(".")[0])
                    results.append({"slot":sn,"name":str(sn),"file":f,"display":get_ck_world_name(game_key,cfg,sn)})
                except: pass
    elif slot_type=="hex":
        for hex_id,slot_num in ENSHROUDED_HEX_TO_SLOT.items():
            f=folder/hex_id
            # Check for any numbered backup file (-1, -2, -3 etc)
            # Enshrouded doesn't always start at -1
            has_backup = any((folder/f"{hex_id}-{i}").exists() for i in range(1,10))
            if f.exists() and f.is_file() and has_backup:
                results.append({"slot":slot_num,"hex_id":hex_id,"name":hex_id,"file":f,"display":None})
    return sorted(results,key=lambda x:x["slot"])

def get_local_worlds(game_key,cfg):
    info=GAMES.get(game_key,{})
    if info.get("slot_based"): return get_slot_worlds(game_key,cfg)
    folder=find_save_folder(game_key,cfg)
    if not folder: return []
    ext=info.get("save_ext",""); backup=info.get("backup_pattern","_backup")
    # Internal Hearth files that should never appear as worlds
    INTERNAL_NAMES={"hearth_status","hearth.lock",".hearth_lock"}
    results=[]
    for f in folder.iterdir():
        if f.is_file() and ext and f.name.endswith(ext) and backup not in f.name and ".mine" not in f.name:
            if f.stem in INTERNAL_NAMES: continue
            results.append({"name":f.stem,"file":f,"display":f.stem,"slot":None})
    return sorted(results,key=lambda x:x["name"].lower())

def get_local_save_file_by_name(game_key,cfg,world_name):
    """Get the specific local save file for a named world."""
    info=GAMES.get(game_key,{})
    if info.get("slot_based"): return None  # Slot games handled differently
    folder=find_save_folder(game_key,cfg)
    if not folder: return None
    ext=info.get("save_ext","")
    if not ext: return None
    f=folder/f"{world_name}{ext}"
    return f if f.exists() else None

def get_enshrouded_files(folder, hex_id):
    """Get all files for an Enshrouded hex slot including any numbered backups."""
    # Base files
    patterns = [hex_id, f"{hex_id}_info", f"{hex_id}_info-index", f"{hex_id}-index"]
    # Add any numbered backups that exist (-1, -2, -3 etc)
    for i in range(1, 10):
        patterns.append(f"{hex_id}-{i}")
        patterns.append(f"{hex_id}_info-{i}")
    return [folder/p for p in patterns if (folder/p).exists()]

def find_free_enshrouded_slot(folder):
    # A slot is only truly occupied if the main hex file AND at least one numbered
    # backup (-1 through -9) exist. Enshrouded pre-creates all 10 hex files as
    # placeholders even for empty slots, so existence alone is not enough.
    for sn,hx in ENSHROUDED_SLOTS.items():
        main_exists = (folder/hx).exists()
        has_backup = any((folder/f"{hx}-{i}").exists() for i in range(1,10))
        if not (main_exists and has_backup): return sn,hx
    return None,None

def find_free_ck_slot(folder,ext=".world.gzip"):
    for i in range(20):
        if not (folder/f"{i}{ext}").exists(): return i
    return None

# ── Drive helpers ─────────────────────────────────────────────────────────────
def _sanitize_world_name(name):
    """Strip leading/trailing spaces and replace illegal Windows path characters."""
    import re
    name=str(name).strip()
    name=re.sub(r'[\\/:*?"<>|]','_',name)
    return name or "unnamed_world"

def get_drive_world_folder(drive,game_key,owner,world_id):
    p=Path(drive)/game_key/owner/_sanitize_world_name(world_id); p.mkdir(parents=True,exist_ok=True); return p

def write_meta(wf,owner,world_id,display_name=""):
    with open(Path(wf)/META_FILENAME,"w") as f:
        json.dump({"owner":owner,"world":str(world_id),"display_name":display_name,
                   "updated":ts_full(),"copyright":COPYRIGHT},f)

def read_meta(wf):
    m=Path(wf)/META_FILENAME
    if m.exists():
        try:
            with open(m) as f: return json.load(f)
        except: pass
    return None

def write_worldmap(wf,mapping):
    with open(Path(wf)/MAP_FILENAME,"w") as f: json.dump(mapping,f,indent=2)

def read_worldmap(wf):
    m=Path(wf)/MAP_FILENAME
    if m.exists():
        try:
            with open(m) as f: return json.load(f)
        except: pass
    return {}

def _read_lock(wf):
    lf=Path(wf)/LOCK_FILENAME
    if lf.exists():
        try:
            with open(lf) as f: return json.load(f)
        except: pass
    return None

def _write_lock(wf,username):
    with open(Path(wf)/LOCK_FILENAME,"w") as f:
        json.dump({"user":username,"since":datetime.now().isoformat()},f)

def _clear_lock(wf,username=None):
    lf=Path(wf)/LOCK_FILENAME
    if not lf.exists(): return
    if username:
        d=_read_lock(wf)
        if d and d.get("user")!=username: return
    lf.unlink(missing_ok=True)

def _lock_age_hours(lock):
    try: return (datetime.now()-datetime.fromisoformat(lock.get("since",""))).total_seconds()/3600
    except: return 0

def _trim_backups(world_backup_dir):
    """Keep only the MAX_BACKUPS most recent backup folders, delete the rest."""
    try:
        folders = sorted(
            [d for d in world_backup_dir.iterdir() if d.is_dir()],
            key=lambda d: d.name  # timestamp format sorts chronologically
        )
        while len(folders) > MAX_BACKUPS:
            oldest = folders.pop(0)
            try: shutil.rmtree(oldest)
            except Exception: pass
    except Exception:
        pass

def backup_local(local_file, game_key, owner, world_id):
    """Back up a single file before overwriting. Keeps rolling MAX_BACKUPS."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    world_dir = BACKUP_FOLDER / game_key / owner / str(world_id)
    dest = world_dir / stamp
    dest.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(local_file, dest / Path(local_file).name)
        _trim_backups(world_dir)
        return True
    except Exception:
        return False

def backup_slot(folder, hex_id, game_key, owner, world_id):
    """Back up ALL files for an Enshrouded hex slot before overwriting."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    world_dir = BACKUP_FOLDER / game_key / owner / str(world_id)
    dest = world_dir / stamp
    dest.mkdir(parents=True, exist_ok=True)
    backed = 0
    for f in folder.iterdir():
        if f.is_file() and f.name.startswith(hex_id):
            try:
                shutil.copy2(f, dest / f.name)
                backed += 1
            except Exception:
                pass
    if backed:
        _trim_backups(world_dir)
    return backed

# ── Status file — cross-PC communication through Drive ────────────────────────
def write_status(wf, username, file_hash_val, verified=True):
    """Write hearth_status.json to a world's Drive folder after push."""
    try:
        data = {
            "username": username,
            "last_push": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_hash": file_hash_val or "",
            "verified": verified,
            "version": VERSION,
        }
        with open(Path(wf)/STATUS_FILENAME, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def read_status(wf):
    """Read hearth_status.json from a world's Drive folder."""
    try:
        p = Path(wf)/STATUS_FILENAME
        if not p.exists(): return None
        with open(p) as f: return json.load(f)
    except Exception:
        return None

def read_all_statuses(drive, game_key, world_id):
    """Read status files from all players' Drive folders for a given world."""
    base = Path(drive) / game_key
    statuses = []
    if not base.exists(): return statuses
    try:
        for owner_dir in base.iterdir():
            if not owner_dir.is_dir(): continue
            wf = owner_dir / str(world_id)
            if not wf.exists(): continue
            s = read_status(wf)
            if s:
                s["owner"] = owner_dir.name
                s["folder"] = str(wf)
                statuses.append(s)
    except Exception:
        pass
    return statuses

def get_all_shared_worlds(drive,game_key):
    base=Path(drive)/game_key
    if not base.exists(): return []
    INTERNAL_DIRS={"hearth_status",".hearth_lock"}
    results=[]
    for od in base.iterdir():
        if not od.is_dir(): continue
        for wd in od.iterdir():
            if not wd.is_dir(): continue
            if wd.name in INTERNAL_DIRS: continue
            meta=read_meta(wd); lock=_read_lock(wd)
            try:
                has=any(True for _ in wd.iterdir())
            except: has=False
            if has:
                results.append({"owner":od.name,"world_id":wd.name,
                    "display_name":meta.get("display_name",wd.name) if meta else wd.name,
                    "folder":wd,"lock":lock,"meta":meta})
    return results

def safe_copy(src,dst):
    """Copy file with retry on Drive lock."""
    for attempt in range(3):
        try: shutil.copy2(src,dst); return True
        except PermissionError:
            if attempt<2: time.sleep(1)
        except Exception: return False
    return False

# ── Game-specific push functions ──────────────────────────────────────────────
def _push_enshrouded(drive, username, world_entry, cfg, display_name=""):
    """Push an Enshrouded world to Drive.
    
    For your OWN world: hex_id is the local hex, push under that same hex folder.
    For SOMEONE ELSE'S world you're pushing back: local_hex may differ from remote_hex.
    We check the worldmap to find the correct remote folder name to push back to.
    """
    local_hex = world_entry.get("hex_id","")
    if not local_hex:
        return False
    folder = find_save_folder("Enshrouded", cfg)
    if not folder:
        return False

    # Check if this local_hex is actually a remapped copy of someone else's world
    # by scanning all shared world folders for a worldmap entry pointing to this local_hex
    remote_hex = local_hex  # Default: pushing your own world, hex stays the same
    owner = username         # Default: you are the owner

    base = Path(drive) / "Enshrouded"
    if base.exists():
        for owner_dir in base.iterdir():
            if not owner_dir.is_dir(): continue
            for world_dir in owner_dir.iterdir():
                if not world_dir.is_dir(): continue
                wmap = read_worldmap(world_dir)
                # Case-insensitive lookup — usernames may have been stored lowercase
                wmap_lower = {k.lower(): v for k, v in wmap.items()}
                my = wmap_lower.get(username.lower(), {})
                if my.get("local_hex") == local_hex:
                    # Found it — this local slot belongs to owner_dir.name's world
                    remote_hex = world_dir.name
                    owner = owner_dir.name
                    break
            if owner != username:
                break

    wf = get_drive_world_folder(drive, "Enshrouded", owner, remote_hex)
    files = get_enshrouded_files(folder, local_hex)
    if not files:
        return False
    # Copy files, renaming from local_hex back to remote_hex
    for f in files:
        remote_name = remote_hex + f.name[len(local_hex):]
        safe_copy(f, wf / remote_name)
    write_meta(wf, owner, remote_hex, display_name or world_entry.get("display", remote_hex))
    return True

def _push_core_keeper(drive, username, world_entry, cfg, display_name=""):
    src = world_entry.get("file")
    if not src or not Path(str(src)).exists():
        return False
    slot = world_entry.get("slot", 0)
    world_id = str(slot)
    wf = get_drive_world_folder(drive, "Core Keeper", username, world_id)
    safe_copy(src, wf / Path(str(src)).name)
    inf = find_info_folder("Core Keeper", cfg)
    if inf:
        wif = inf / f"{slot}.worldinfo"
        if wif.exists():
            safe_copy(wif, wf / wif.name)
    write_meta(wf, username, world_id, display_name or world_entry.get("display", world_id))
    return True

def _push_standard(drive, game_key, username, world_entry, cfg, display_name=""):
    src = world_entry.get("file")
    if not src or not Path(str(src)).exists():
        return False
    world_id = world_entry.get("name","")
    # Validate world_id before touching Drive — prevents empty/None folders
    if not world_id or world_id == "None" or ".mine" in str(world_id):
        return False
    wf = get_drive_world_folder(drive, game_key, username, world_id)
    safe_copy(src, wf / Path(str(src)).name)
    info = GAMES.get(game_key, {})
    pe = info.get("paired_ext")
    if pe:
        paired = Path(str(src)).with_suffix(pe)
        if paired.exists():
            safe_copy(paired, wf / paired.name)
    write_meta(wf, username, world_id, display_name or world_entry.get("display", world_id))
    # Compute hash of local file and write status — used for cross-PC verification
    local_hash = file_hash(str(src))
    # Verify push — hash local against what landed on Drive
    drive_copy = wf / Path(str(src)).name
    drive_hash = file_hash(str(drive_copy)) if drive_copy.exists() else None
    verified = (local_hash == drive_hash) if local_hash and drive_hash else False
    write_status(wf, username, local_hash, verified=verified)
    return verified if (local_hash and drive_hash) else True  # return True if can't verify (Drive still syncing)

def push_world(drive, game_key, username, world_entry, cfg, display_name=""):
    try:
        if game_key == "Enshrouded":
            return _push_enshrouded(drive, username, world_entry, cfg, display_name)
        elif game_key == "Core Keeper":
            return _push_core_keeper(drive, username, world_entry, cfg, display_name)
        else:
            return _push_standard(drive, game_key, username, world_entry, cfg, display_name)
    except Exception:
        return False

# ── Game-specific pull functions ──────────────────────────────────────────────
def _pull_enshrouded(drive, owner, world_entry, cfg, is_own=False):
    remote_hex = world_entry.get("world_id","")
    if not remote_hex:
        return False, "no_world_id"
    wf = Path(drive) / "Enshrouded" / owner / remote_hex
    if not wf.exists():
        return False, "no_remote"
    folder = find_save_folder("Enshrouded", cfg)
    if not folder:
        return False, "no_local_path"
    username = cfg.get("username","")
    wmap = read_worldmap(wf)
    # Case-insensitive lookup — usernames may have been stored lowercase
    wmap_lower = {k.lower(): v for k, v in wmap.items()}
    my = wmap_lower.get(username.lower(), {})
    local_hex = my.get("local_hex")
    if local_hex and not (folder / local_hex).exists():
        local_hex = None
    if not local_hex:
        _, local_hex = find_free_enshrouded_slot(folder)
        if not local_hex:
            return False, "no_free_slot"
        my["local_hex"] = local_hex
        # Always store with exact username casing from config
        # Remove any existing lowercase version first
        wmap = {k: v for k, v in wmap.items() if k.lower() != username.lower()}
        wmap[username] = my
        write_worldmap(wf, wmap)
    # Always back up the entire local slot before overwriting — no exceptions
    if (folder / local_hex).exists():
        backup_slot(folder, local_hex, "Enshrouded", owner, remote_hex)

    copied = 0
    for f in wf.iterdir():
        if f.name in (LOCK_FILENAME, META_FILENAME, MAP_FILENAME, LOG_FILENAME, STATUS_FILENAME):
            continue
        if not f.name.startswith(remote_hex):
            continue
        local_name = local_hex + f.name[len(remote_hex):]
        local_dest = folder / local_name
        safe_copy(f, local_dest)
        copied += 1

    # Do NOT touch the index files. The sender's index value is correct as-is.
    # Enshrouded will read "latest": N and load the correct numbered backup.
    # Manual testing confirmed: rename files only, leave index alone = world loads correctly.

    return (True, "ok") if copied > 0 else (False, "no_files_copied")

def _pull_core_keeper(drive, owner, world_entry, cfg, is_own=False):
    world_id = world_entry.get("world_id","")
    wf = Path(drive) / "Core Keeper" / owner / world_id
    if not wf.exists():
        return False, "no_remote"
    folder = find_save_folder("Core Keeper", cfg)
    if not folder:
        return False, "no_local_path"
    username = cfg.get("username","")
    ext = ".world.gzip"
    wmap = read_worldmap(wf)
    my = wmap.get(username, {})
    local_slot = my.get("local_slot")
    if local_slot is not None and not (folder / f"{local_slot}{ext}").exists():
        local_slot = None
    if local_slot is None:
        local_slot = find_free_ck_slot(folder, ext)
        if local_slot is None:
            return False, "no_free_slot"
        my["local_slot"] = local_slot
        wmap[username] = my
        write_worldmap(wf, wmap)
    for f in wf.iterdir():
        if f.name.endswith(ext):
            ld = folder / f"{local_slot}{ext}"
            if is_own and ld.exists():
                backup_local(ld, "Core Keeper", owner, world_id)
            safe_copy(f, ld)
    inf = find_info_folder("Core Keeper", cfg)
    if inf:
        for f in wf.iterdir():
            if ".worldinfo" in f.name:
                safe_copy(f, inf / f"{local_slot}.worldinfo")
    return True, "ok"

def _pull_standard(drive, game_key, owner, world_entry, cfg, is_own=False):
    world_id = world_entry.get("world_id","")
    if not world_id or world_id == "None":
        return False, "bad_world_id"
    wf = Path(drive) / game_key / owner / world_id
    if not wf.exists():
        return False, "no_remote"
    folder = find_save_folder(game_key, cfg)
    if not folder:
        return False, "no_local_path"
    info = GAMES.get(game_key, {})
    ext = info.get("save_ext","")
    paired_ext = info.get("paired_ext")
    copied = 0
    for f in wf.iterdir():
        if f.name in (LOCK_FILENAME, META_FILENAME, MAP_FILENAME, LOG_FILENAME, STATUS_FILENAME):
            continue
        # Only copy files matching this game's save extension or paired extension
        if ext and not f.name.endswith(ext) and not (paired_ext and f.name.endswith(paired_ext)):
            continue
        # Skip backup files — don't pull backups into local save folder
        backup_pat = info.get("backup_pattern","_backup")
        if backup_pat and backup_pat in f.name:
            continue
        ld = folder / f.name
        # Always back up before overwriting — regardless of is_own
        if ld.exists():
            backup_local(ld, game_key, owner, world_id)
        safe_copy(f, ld)
        copied += 1
    return (True, "ok") if copied > 0 else (False, "no_files_copied")

def pull_world(drive, game_key, owner, world_entry, cfg, is_own=False):
    try:
        if game_key == "Enshrouded":
            return _pull_enshrouded(drive, owner, world_entry, cfg, is_own)
        elif game_key == "Core Keeper":
            return _pull_core_keeper(drive, owner, world_entry, cfg, is_own)
        else:
            return _pull_standard(drive, game_key, owner, world_entry, cfg, is_own)
    except Exception as e:
        return False, str(e)


def file_hash(path):
    """MD5 hash of file content. Fast and reliable for save file comparison."""
    try:
        h=hashlib.md5()
        with open(path,"rb") as f:
            for chunk in iter(lambda:f.read(65536),b""): h.update(chunk)
        return h.hexdigest()
    except: return None

def _hash_file(path):
    """MD5 hash of a single file. Returns None on error."""
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def _drive_files(wf):
    """Return list of save files in a Drive world folder (excludes meta files)."""
    EXCLUDE = {LOCK_FILENAME, META_FILENAME, MAP_FILENAME, LOG_FILENAME, STATUS_FILENAME}
    try:
        return [f for f in Path(wf).iterdir()
                if f.is_file() and f.name not in EXCLUDE]
    except Exception:
        return []

def compare_local_and_drive(drive, game_key, owner, world_id, cfg):
    """
    Compare local save file to Drive copy using hash then timestamp.
    Returns:
      "same"         — identical content, nothing to do
      "drive_newer"  — Drive copy is newer, should pull
      "local_newer"  — local copy is newer, should push
      "drive_only"   — file exists on Drive but not locally
      "local_only"   — file exists locally but not on Drive
      "conflict"     — files differ but timestamps too close to decide
      "unknown"      — can't determine (missing data)
    """
    info = GAMES.get(game_key, {})
    ext  = info.get("save_ext", "")
    if not ext or info.get("slot_based"): return "unknown"

    folder = find_save_folder(game_key, cfg)
    local_file = (folder / f"{world_id}{ext}") if folder else None

    wf = Path(drive) / game_key / owner / str(world_id)
    remote_files = _drive_files(wf) if wf.exists() else []
    remote_file = next((f for f in remote_files if f.name.endswith(ext)), None)

    local_exists  = local_file and local_file.exists()
    remote_exists = remote_file and remote_file.exists()

    if not local_exists and not remote_exists: return "unknown"
    if not local_exists and remote_exists:     return "drive_only"
    if local_exists and not remote_exists:     return "local_only"

    # Both exist — compare hashes first
    local_hash  = _hash_file(str(local_file))
    remote_hash = _hash_file(str(remote_file))

    if local_hash and remote_hash and local_hash == remote_hash:
        return "same"

    # Hashes differ — use timestamps to decide who wins
    try:
        local_mtime  = local_file.stat().st_mtime
        remote_mtime = remote_file.stat().st_mtime
        diff = local_mtime - remote_mtime

        if abs(diff) < 120:  # Within 2 minutes — too close to call safely
            return "conflict"
        elif diff > 0:
            return "local_newer"
        else:
            return "drive_newer"
    except Exception:
        return "conflict"

def is_drive_newer(drive, game_key, owner, world_id, cfg):
    """
    Returns True only if Drive has content that differs from local.
    Uses file hashes — timestamp differences alone are not enough.
    This prevents the pull feedback loop where Drive syncing updates
    timestamps and tricks Hearth into pulling identical files repeatedly.
    """
    wf = Path(drive) / game_key / owner / str(world_id)
    if not wf.exists():
        return False

    remote_files = _drive_files(wf)
    if not remote_files:
        return False

    folder = find_save_folder(game_key, cfg)
    if not folder or not folder.exists():
        # No local folder at all — Drive is definitely newer
        return True

    info = GAMES.get(game_key, {})
    ext  = info.get("save_ext", "")

    # For standard games: compare the specific world file by hash
    if ext and not info.get("slot_based"):
        local_file = folder / f"{world_id}{ext}"
        if not local_file.exists():
            return True  # File doesn't exist locally — pull it
        remote_match = next((f for f in remote_files if f.name.endswith(ext)), None)
        if not remote_match:
            return False
        return _hash_file(remote_match) != _hash_file(local_file)

    # For Enshrouded: compare the main hex file by hash
    if info.get("slot_type") == "hex":
        # Find which local hex this remote world maps to via worldmap
        wmap = read_worldmap(wf)
        username = cfg.get("username", "")
        my = wmap.get(username, {})
        local_hex = my.get("local_hex", world_id)
        local_file = folder / local_hex
        remote_file = next((f for f in remote_files
                            if f.name == world_id), None)
        if not remote_file:
            return False
        if not local_file.exists():
            return True
        return _hash_file(remote_file) != _hash_file(local_file)

    # For Core Keeper: compare by slot number
    if info.get("slot_type") == "numeric":
        wmap = read_worldmap(wf)
        username = cfg.get("username", "")
        my = wmap.get(username, {})
        local_slot = my.get("local_slot")
        slot_ext = info.get("save_ext", ".world.gzip")
        if local_slot is None:
            return True
        local_file = folder / f"{local_slot}{slot_ext}"
        remote_file = next((f for f in remote_files
                            if f.name.endswith(slot_ext)), None)
        if not remote_file:
            return False
        if not local_file.exists():
            return True
        return _hash_file(remote_file) != _hash_file(local_file)

    # Fallback: timestamp-based (60 second buffer)
    remote_t = max(f.stat().st_mtime for f in remote_files)
    local_files = [f for f in folder.iterdir() if f.is_file()]
    if not local_files:
        return True
    local_t = max(f.stat().st_mtime for f in local_files)
    return remote_t - local_t > 60

# ── App ───────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class Hearth(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Hearth v{VERSION}")
        self.resizable(True,True)
        self.minsize(520,680)
        self.configure(fg_color=C["bg"])
        if ICO_PATH.exists():
            try: self.iconbitmap(str(ICO_PATH))
            except: pass
        w,h=600,940; sw=self.winfo_screenwidth(); sh=self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{sw//6}+{max(30,(sh-h)//2-30)}")

        self.cfg=load_config()
        self.shared_worlds=self.cfg.get("shared_worlds",{})
        self.world_labels=self.cfg.get("world_labels",{})
        self.participated_worlds=self.cfg.get("participated_worlds",{})  # per-world opt-in for others' worlds
        self._collapsed_games=set(self.cfg.get("collapsed_games",[]))
        self.first_pull_shown=self.cfg.get("first_pull_shown",False)
        self.first_share_shown=self.cfg.get("first_share_shown",False)
        self.monitor_running=False
        self.game_was_running=None
        self.monitor_thread=None
        self.tray_icon=None
        self._syncing=False
        self._world_widgets={}
        self._last_scan_hash=""
        self._world_widgets={}   # key->(row_frame, status_lbl, mtime_lbl)
        self._world_keys_ordered=[]  # ordered list of keys for comparison
        self._last_scan_hash=""  # detect when structure changed

        self._build_menu()
        self._build_ui()
        self._load_fields()
        self.protocol("WM_DELETE_WINDOW",self._minimize_or_close)

        if is_first_run(self.cfg): self.after(400,self._show_setup_wizard)
        else: self._startup_checks()
        # Recurring stale lock scan — every 10 minutes, self-owned locks only
        self.after(600000, self._recurring_stale_lock_scan)
        # Drive reachability check — on startup and every 30 minutes
        self.after(500, self._check_drive_reachable)
        self.after(1800000, self._recurring_drive_check)

    # ── System tray ───────────────────────────────────────────────────────────
    def _load_tray_img(self, path):
        """Load a tray icon image, fall back to default if missing."""
        try:
            if Path(path).exists():
                return PILImage.open(str(path)).convert("RGBA").resize((64,64))
        except Exception:
            pass
        # Fallback to original icon
        if ICO_PATH.exists():
            return PILImage.open(str(ICO_PATH)).convert("RGBA").resize((64,64))
        return None

    def _start_tray(self):
        if not HAVE_TRAY: return
        try:
            img = self._load_tray_img(TRAY_ORANGE_PATH)
            if not img: return
            menu=TrayMenu(
                TrayItem("Open Hearth", lambda icon,item: self.after(0,self._show_window), default=True),
                TrayItem("Sync Now",lambda icon,item: self.after(0,self._sync_now)),
                TrayMenu.SEPARATOR,
                TrayItem("Exit",lambda icon,item: self.after(0,self._on_close)),
            )
            self.tray_icon=TrayIcon("Hearth", img, "Hearth", menu)
            t=threading.Thread(target=self.tray_icon.run,daemon=True)
            t.start()
        except Exception as e:
            self._log(f"Tray error: {e}")

    def _check_for_update(self):
        """Hit GitHub releases API in background. If newer version found, go blue and pop up once."""
        def _worker():
            try:
                req = urllib.request.Request(GITHUB_API, headers={"User-Agent": "Hearth"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode())
                tag = data.get("tag_name", "").lstrip("v").strip()
                if not tag:
                    return
                # Simple version compare — split on dots, compare numerically
                def _ver(s):
                    try: return tuple(int(x) for x in s.split("."))
                    except: return (0,)
                if _ver(tag) > _ver(VERSION):
                    self.after(0, lambda: self._notify_update(tag))
            except Exception:
                pass  # silently ignore — network down, rate limit, etc.
        threading.Thread(target=_worker, daemon=True).start()

    def _fetch_fund_progress(self):
        """Fetch fundraiser amount raised from GitHub Gist in background."""
        def _worker():
            try:
                req = urllib.request.Request(CERT_GIST_URL, headers={"User-Agent":"Hearth"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode())
                raised = float(data.get("raised", 0))
                self.after(0, lambda: self._update_fund_banner(raised))
            except Exception:
                pass  # gist may not exist yet — silently ignore
        threading.Thread(target=_worker, daemon=True).start()

    def _update_fund_banner(self, raised):
        """Update the fundraiser progress bar with fetched amount."""
        if not hasattr(self, "_fund_bar") or not self._fund_bar.winfo_exists():
            return
        pct = min(raised / CERT_GOAL, 1.0)
        self._fund_bar.set(pct)
        if hasattr(self, "_fund_label"):
            self._fund_label.configure(text=f"${raised:.0f} of ${CERT_GOAL:.0f} raised")

    def _notify_update(self, new_version):
        """Turn tray blue and show a non-blocking update popup."""
        self._set_tray_icon("update")
        self._log(f"🔵 Update available: v{new_version} — github.com/{GITHUB_REPO}/releases")
        # Non-blocking popup using a Toplevel so the main window keeps working
        popup = ctk.CTkToplevel(self)
        popup.title("Hearth Update Available")
        popup.geometry("360x160")
        popup.resizable(False, False)
        popup.grab_set()
        ctk.CTkLabel(popup,
            text=f"Hearth v{new_version} is available.\nYou're on v{VERSION}.",
            font=ctk.CTkFont("Segoe UI", 13), justify="center").pack(pady=(24, 12))
        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.pack(pady=(0, 16))
        ctk.CTkButton(btn_row, text="Open GitHub",
            fg_color=C["accent"], hover_color=C["accent2"],
            command=lambda: (subprocess.Popen(["start", GITHUB_RELEASES], shell=True), popup.destroy())
        ).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Dismiss",
            fg_color=C["card"], hover_color=C["border"], text_color=C["muted"],
            command=popup.destroy).pack(side="left", padx=8)

    def _set_tray_icon(self, state):
        """Swap tray icon based on state: 'nominal', 'update', 'syncing', 'error'"""
        if not HAVE_TRAY or not self.tray_icon: return
        paths = {
            "nominal": TRAY_ORANGE_PATH,
            "update":  TRAY_BLUE_PATH,
            "syncing": TRAY_GREEN_PATH,
            "error":   TRAY_RED_PATH,
        }
        img = self._load_tray_img(paths.get(state, TRAY_ORANGE_PATH))
        if img:
            try: self.tray_icon.icon = img
            except Exception: pass

    def _show_window(self):
        self.deiconify(); self.lift(); self.focus_force()

    def _hide_window(self):
        self.withdraw()

    # ── Menu ──────────────────────────────────────────────────────────────────
    def _build_menu(self):
        mb=ctk.CTkFrame(self,fg_color=C["surface"],height=36,corner_radius=0)
        mb.pack(fill="x",side="top"); mb.pack_propagate(False)
        ctk.CTkFrame(self,fg_color=C["accent"],height=2,corner_radius=0).pack(fill="x",side="top")
        for label,cmd in [("File",self._menu_file),("Worlds",self._menu_worlds),
                          ("Game",self._menu_game),("Help",self._menu_help)]:
            ctk.CTkButton(mb,text=label,width=60,height=28,fg_color="transparent",
                hover_color=C["card"],text_color=C["muted"],font=ctk.CTkFont("Segoe UI",12),
                corner_radius=4,command=cmd).pack(side="left",padx=2,pady=4)
        ctk.CTkLabel(mb,text=f"v{VERSION}",font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["border"]).pack(side="right",padx=12)

    def _popup(self,items):
        win=ctk.CTkToplevel(self); win.configure(fg_color=C["card"])
        win.resizable(False,False); win.overrideredirect(True)
        h=sum(34 if i[0]!="---" else 8 for i in items)+8
        win.geometry(f"220x{h}+{self.winfo_x()+4}+{self.winfo_y()+70}")
        win.bind("<FocusOut>",lambda e:win.after(100,win.destroy)); win.after(50,win.focus_set)
        for label,cmd in items:
            if label=="---": ctk.CTkFrame(win,fg_color=C["border"],height=1).pack(fill="x",padx=8,pady=2)
            else:
                def mk(c,w=win):
                    def _(): w.destroy(); c() if c else None
                    return _
                ctk.CTkButton(win,text=label,anchor="w",fg_color="transparent",
                    hover_color=C["card2"],text_color=C["text"],font=ctk.CTkFont("Segoe UI",12),
                    height=32,corner_radius=4,command=mk(cmd)).pack(fill="x",padx=4,pady=1)

    def _menu_file(self):
        self._popup([("Open Backup Folder",self._open_backups),
                     ("---",None),("Exit",self._on_close)])

    def _menu_worlds(self):
        self._popup([("Sync Now",self._sync_now),("Unlock All",self._manual_unlock),
                     ("---",None),("Invite a Friend",self._show_invite),
                     ("---",None),("Refresh",self._scan_all_worlds)])

    def _menu_game(self):
        self._popup([("Add Game",self._show_add_game),
                     ("Show / Hide Games",self._show_game_filter),
                     ("---",None),
                     ("Set Custom Save Path",self._browse_save_manual),
                     ("Steam Cloud Help",self._steam_cloud_help)])

    def _menu_help(self):
        self._popup([("How to Find Your Steam ID",self._help_steam_id),
                     ("How to Set Up Shared Folder",self._help_shared_folder),
                     ("World Naming Rules",self._show_naming_rules),
                     ("Status",self._show_status),
                     ("Changelog",self._show_changelog),
                     ("Report a Bug / Request a Feature",self._open_support),
                     ("---",None),("About Hearth",self._show_about)])

    # ── Setup wizard ──────────────────────────────────────────────────────────
    def _show_setup_wizard(self):
        win=ctk.CTkToplevel(self); win.title("Welcome to Hearth")
        win.geometry("480x520"); win.configure(fg_color=C["bg"])
        win.grab_set(); win.resizable(False,False)
        ctk.CTkFrame(win,fg_color=C["accent"],height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,text="🔥  Welcome to Hearth",font=ctk.CTkFont("Segoe UI",20,"bold"),
                     text_color=C["text"]).pack(pady=(20,4))
        ctk.CTkLabel(win,text="Share game worlds with your crew. No server required.",
                     font=ctk.CTkFont("Segoe UI",12),text_color=C["muted"]).pack(pady=(0,12))
        card=ctk.CTkFrame(win,fg_color=C["card"],corner_radius=12)
        card.pack(fill="x",padx=24,pady=(0,8))
        def field(p,lbl,hint=None):
            ctk.CTkLabel(p,text=lbl,font=ctk.CTkFont("Segoe UI",12,"bold"),
                         text_color=C["text"],anchor="w").pack(fill="x",padx=16,pady=(12,0))
            if hint: ctk.CTkLabel(p,text=hint,font=ctk.CTkFont("Segoe UI",10),
                         text_color=C["muted"],anchor="w",wraplength=400).pack(fill="x",padx=16,pady=(1,0))
            e=ctk.CTkEntry(p,fg_color=C["card2"],border_color=C["border"],text_color=C["text"],
                           font=ctk.CTkFont("Segoe UI",12),height=34,corner_radius=6)
            e.pack(fill="x",padx=16,pady=(3,0)); return e
        name_e=field(card,"Your Name","How you appear to others in your group.")
        name_e.insert(0,self.cfg.get("username",""))
        steam_e=field(card,"Steam ID  (Icarus / Core Keeper)",
                      "steamcommunity.com → your profile → number from URL. Leave blank otherwise.")
        steam_e.insert(0,self.cfg.get("steam_id",""))
        ctk.CTkLabel(card,text="Shared Cloud Folder",font=ctk.CTkFont("Segoe UI",12,"bold"),
                     text_color=C["text"],anchor="w").pack(fill="x",padx=16,pady=(12,0))
        ctk.CTkLabel(card,text="Install Google Drive for Desktop → Mirror Files → create HearthSync folder.",
                     font=ctk.CTkFont("Segoe UI",10),text_color=C["muted"],anchor="w",
                     wraplength=400).pack(fill="x",padx=16,pady=(1,0))
        dr=ctk.CTkFrame(card,fg_color="transparent"); dr.pack(fill="x",padx=16,pady=(3,16))
        drive_e=ctk.CTkEntry(dr,fg_color=C["card2"],border_color=C["border"],text_color=C["text"],
                             font=ctk.CTkFont("Segoe UI",12),height=34,corner_radius=6)
        drive_e.pack(side="left",fill="x",expand=True)
        ctk.CTkButton(dr,text="Browse",width=80,height=34,fg_color=C["accent"],
            hover_color=C["accent2"],font=ctk.CTkFont("Segoe UI",11),corner_radius=6,
            command=lambda:drive_e.delete(0,"end") or drive_e.insert(0,
                filedialog.askdirectory(title="Select Shared Folder") or "")).pack(side="left",padx=(8,0))
        ctk.CTkLabel(win,text="⚠  Google Drive must be set to Mirror Files, not Stream Files.",
                     font=ctk.CTkFont("Segoe UI",10),text_color=C["amber"],
                     fg_color=C["card"],corner_radius=6).pack(fill="x",padx=24,pady=(0,8))
        def finish():
            if not name_e.get().strip():
                messagebox.showerror("Hearth","Please enter your name.",parent=win); return
            d=drive_e.get().strip()
            if not d or not Path(d).exists():
                messagebox.showerror("Hearth","Please select a valid shared folder.",parent=win); return
            self.cfg["username"]=name_e.get().strip(); self.cfg["steam_id"]=steam_e.get().strip()
            self.cfg["drive_folder"]=d; save_config(self.cfg)
            self.username_var.set(self.cfg["username"]); self.steam_var.set(self.cfg["steam_id"])
            self.drive_var.set(d); win.destroy(); self._startup_checks()
        ctk.CTkButton(win,text="Get Started →",height=44,fg_color=C["accent"],
            hover_color=C["accent2"],font=ctk.CTkFont("Segoe UI",14,"bold"),
            corner_radius=8,command=finish).pack(fill="x",padx=24,pady=(0,16))

    # ── Startup ───────────────────────────────────────────────────────────────
    def _startup_checks(self):
        self._log(f"🔥 Hearth v{VERSION} starting...")
        self._log(f"   {COPYRIGHT}")
        if not HAVE_PSUTIL: self._log("⚠  psutil missing — run: pip install psutil")
        if not HAVE_WIN32:  self._log("⚠  pywin32 missing — tModLoader detection disabled")
        if not HAVE_TRAY:   self._log("⚠  pystray/pillow missing — system tray disabled. Run: pip install pystray pillow")
        drive=self.cfg.get("drive_folder","")
        if drive:
            dp=Path(drive)
            if not dp.exists():
                self._log("⚠  Drive folder not found. Check Settings — Google Drive may not be synced yet.")
            elif not any(dp.iterdir()):
                self._log("⚠  Drive folder is empty. Make sure Google Drive is set to Mirror Files mode.")
        self._clear_stale_locks()
        self._scan_all_worlds()
        self._auto_sync_on_startup()
        self._start_monitor()
        self._start_tray()
        self._check_for_update()
        self._fetch_fund_progress()

    def _clear_stale_locks(self):
        """Clear stale locks — self-owned locks only. Never touches other users' locks."""
        drive=self.cfg.get("drive_folder",""); username=self.cfg.get("username","")
        if not drive or not username: return
        for gk in GAMES:
            for entry in get_all_shared_worlds(drive,gk):
                lock=entry["lock"]
                if not lock: continue
                if lock.get("user") != username: continue
                if not is_game_running(gk):
                    _clear_lock(entry["folder"],username)
                    self._log(f"🧹 Cleared stale lock: {entry['display_name']}")

    def _recurring_stale_lock_scan(self):
        """Run every 10 minutes. Clears self-owned locks where the game is no longer running."""
        def _worker():
            self._clear_stale_locks()
        threading.Thread(target=_worker,daemon=True).start()
        self.after(600000, self._recurring_stale_lock_scan)

    def _check_drive_reachable(self):
        """Check if the configured Drive folder is accessible. Warn visibly if not."""
        drive=self.cfg.get("drive_folder","")
        if not drive: return
        reachable=Path(drive).exists()
        if not reachable:
            self._log("⚠ Drive folder is unreachable — make sure Google Drive is running.")
            self.after(0,lambda: self._show_drive_warning(True))
        else:
            self.after(0,lambda: self._show_drive_warning(False))

    def _show_drive_warning(self,show):
        """Show or hide a persistent Drive warning banner at the top of the UI."""
        if show:
            if not hasattr(self,"_drive_warn_bar") or not self._drive_warn_bar.winfo_exists():
                self._drive_warn_bar=ctk.CTkFrame(self,fg_color="#7a1a00",corner_radius=0,height=30)
                self._drive_warn_bar.pack(fill="x",before=self.winfo_children()[0])
                ctk.CTkLabel(self._drive_warn_bar,
                    text="⚠  Google Drive folder is unreachable — make sure Google Drive is running",
                    text_color="#ffddcc",font=ctk.CTkFont("Segoe UI",11)).pack(pady=5)
        else:
            if hasattr(self,"_drive_warn_bar"):
                try: self._drive_warn_bar.destroy()
                except: pass

    def _recurring_drive_check(self):
        """Re-check Drive reachability every 30 minutes."""
        self._check_drive_reachable()
        self.after(1800000, self._recurring_drive_check)

    def _auto_sync_on_startup(self):
        """Smart startup sync — hash+timestamp to decide push or pull. Never blindly overwrites."""
        def _worker():
            drive=self.cfg.get("drive_folder",""); username=self.cfg.get("username","")
            if not drive or not username: return

            # ── Others' shared worlds ─────────────────────────────────────────
            for gk in GAMES:
                for entry in get_all_shared_worlds(drive,gk):
                    if entry["owner"]==username: continue
                    if entry["lock"]: continue
                    # Skip worlds user hasn't opted into
                    if not self.participated_worlds.get(gk,{}).get(entry["world_id"],False): continue
                    try:
                        result = compare_local_and_drive(drive,gk,entry["owner"],
                                                         entry["world_id"],self.cfg)
                        name = entry["display_name"]
                        if result == "same":
                            self._log(f"✓ Startup check: {name} — already in sync")
                        elif result == "drive_newer":
                            ok,_=pull_world(drive,gk,entry["owner"],entry,self.cfg,is_own=False)
                            if ok: self._log(f"⬇ Startup pulled: {name} — Drive was newer")
                            else:  self._log(f"⚠ Startup pull failed: {name}")
                        elif result == "drive_only":
                            ok,_=pull_world(drive,gk,entry["owner"],entry,self.cfg,is_own=False)
                            if ok: self._log(f"⬇ Startup pulled: {name} — new world")
                        elif result in ("local_newer","local_only"):
                            self._log(f"✓ Startup check: {name} — local is newer, no pull needed")
                        elif result == "conflict":
                            info=GAMES.get(gk,{}); ext=info.get("save_ext","")
                            folder=find_save_folder(gk,self.cfg)
                            lf=folder/f"{entry['world_id']}{ext}" if folder and ext else None
                            self._log(f"⚠ Startup conflict detected: {name} — showing resolution options")
                            if lf and lf.exists():
                                self.after(2000,lambda g=gk,w=entry["world_id"],f=lf:
                                    self._check_conflict(g,w,f))
                        else:
                            self._log(f"? Startup check: {name} — could not determine sync state")
                    except Exception as e:
                        self._log(f"⚠ Startup check error ({entry.get('display_name','')}): {e}")

            # ── Own shared worlds ─────────────────────────────────────────────
            for gk in GAMES:
                for wid,shared in self.shared_worlds.get(gk,{}).items():
                    if not shared: continue
                    try:
                        result = compare_local_and_drive(drive,gk,username,wid,self.cfg)
                        if result == "same":
                            self._log(f"✓ Startup check: {wid} ({gk}) — in sync")
                        elif result == "drive_newer":
                            # Drive is newer than local — someone else may have played this world
                            worlds=get_local_worlds(gk,self.cfg)
                            we=next((w for w in worlds if w["name"]==wid),{"name":wid,"file":None})
                            ok,_=pull_world(drive,gk,username,we,self.cfg,is_own=True)
                            if ok: self._log(f"⬇ Startup pulled own world: {wid} — Drive was newer")
                            else:  self._log(f"⚠ Startup pull failed for own world: {wid}")
                        elif result == "local_newer":
                            # Local is newer — push it to Drive
                            worlds=get_local_worlds(gk,self.cfg)
                            we=next((w for w in worlds if w["name"]==wid),None)
                            if we:
                                ok=push_world(drive,gk,username,we,self.cfg)
                                if ok: self._log(f"⬆ Startup pushed: {wid} — local was newer than Drive")
                                else:  self._log(f"⚠ Startup push failed: {wid}")
                        elif result == "local_only":
                            # Never been pushed — push now
                            worlds=get_local_worlds(gk,self.cfg)
                            we=next((w for w in worlds if w["name"]==wid),None)
                            if we:
                                ok=push_world(drive,gk,username,we,self.cfg)
                                if ok: self._log(f"⬆ Startup pushed: {wid} — first time to Drive")
                        elif result == "conflict":
                            info=GAMES.get(gk,{}); ext=info.get("save_ext","")
                            folder=find_save_folder(gk,self.cfg)
                            lf=folder/f"{wid}{ext}" if folder and ext else None
                            self._log(f"⚠ Startup conflict on own world: {wid} — showing resolution options")
                            if lf and lf.exists():
                                self.after(2000,lambda g=gk,w=wid,f=lf:
                                    self._check_conflict(g,w,f))
                    except Exception as e:
                        self._log(f"⚠ Startup check error ({wid}): {e}")

            self.after(0,lambda: self._scan_all_worlds())
        threading.Thread(target=_worker,daemon=True).start()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr=ctk.CTkFrame(self,fg_color=C["surface"],height=52,corner_radius=0)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr,text="🔥  Hearth",font=ctk.CTkFont("Segoe UI",22,"bold"),
                     text_color=C["text"]).pack(side="left",padx=20,pady=12)
        donate_lbl=ctk.CTkLabel(hdr,text="Support Hearth ☕",font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["muted"],cursor="hand2")
        donate_lbl.pack(side="right",padx=16)
        donate_lbl.bind("<Button-1>",lambda e:self._open_donate())
        donate_lbl.bind("<Enter>",lambda e:donate_lbl.configure(text_color=C["accent"]))
        donate_lbl.bind("<Leave>",lambda e:donate_lbl.configure(text_color=C["muted"]))

        # ── Fundraiser banner (one-time dismissible) ──────────────────────────
        if not self.cfg.get("fund_banner_dismissed", False):
            self._fund_banner_frame = ctk.CTkFrame(self, fg_color=C["card2"], corner_radius=0, height=88)
            self._fund_banner_frame.pack(fill="x"); self._fund_banner_frame.pack_propagate(False)
            ctk.CTkButton(self._fund_banner_frame, text="✕", width=24, height=24,
                fg_color="transparent", hover_color=C["border"], text_color=C["muted"],
                font=ctk.CTkFont("Segoe UI",11), corner_radius=4,
                command=self._dismiss_fund_banner).pack(side="right", padx=8, pady=4, anchor="n")
            txt_col = ctk.CTkFrame(self._fund_banner_frame, fg_color="transparent")
            txt_col.pack(side="left", fill="x", expand=True, padx=(12,0), pady=6)
            ctk.CTkLabel(txt_col,
                text="⚠  Windows flags Hearth as dangerous — we need a code signing certificate to fix it.",
                font=ctk.CTkFont("Segoe UI",13), text_color=C["amber"], anchor="w").pack(fill="x")
            bar_row = ctk.CTkFrame(txt_col, fg_color="transparent")
            bar_row.pack(fill="x", pady=(3,0))
            self._fund_bar = ctk.CTkProgressBar(bar_row, height=8, corner_radius=4,
                fg_color=C["border"], progress_color=C["accent"])
            self._fund_bar.set(0)
            self._fund_bar.pack(side="left", fill="x", expand=True, padx=(0,8))
            self._fund_label = ctk.CTkLabel(bar_row, text="$0 of $200 raised",
                font=ctk.CTkFont("Segoe UI",12), text_color=C["muted"], width=110, anchor="w")
            self._fund_label.pack(side="left")
            donate_btn = ctk.CTkLabel(txt_col, text="Donate to fix this",
                font=ctk.CTkFont("Segoe UI",11), text_color=C["accent"], cursor="hand2", anchor="w")
            donate_btn.pack(fill="x")
            donate_btn.bind("<Button-1>", lambda e: self._open_donate())
        else:
            self._fund_bar = None
            self._fund_label = None

        self.scroll=ctk.CTkScrollableFrame(self,fg_color=C["bg"],corner_radius=0,
            scrollbar_button_color=C["border"],scrollbar_button_hover_color=C["card2"])
        self.scroll.pack(fill="both",expand=True)
        self._build_config_card()
        self._build_worlds_card()
        self._build_sync_card()
        self._build_log_card()

    def _card(self,title=None):
        outer=ctk.CTkFrame(self.scroll,fg_color=C["card"],corner_radius=12)
        outer.pack(fill="x",padx=16,pady=(0,10))
        if title:
            ctk.CTkLabel(outer,text=title,font=ctk.CTkFont("Segoe UI",11,"bold"),
                         text_color=C["muted"]).pack(anchor="w",padx=16,pady=(12,4))
        return outer

    def _build_config_card(self):
        cf=self._card("CONFIGURATION")
        row=ctk.CTkFrame(cf,fg_color="transparent"); row.pack(fill="x",padx=12,pady=(4,0))
        nf=ctk.CTkFrame(row,fg_color="transparent"); nf.pack(side="left",fill="x",expand=True,padx=(0,6))
        ctk.CTkLabel(nf,text="Your Name",font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["text"],anchor="w").pack(anchor="w")
        self.username_var=ctk.StringVar(value=self.cfg.get("username",""))
        ctk.CTkEntry(nf,textvariable=self.username_var,fg_color=C["card2"],border_color=C["border"],
                     text_color=C["text"],font=ctk.CTkFont("Segoe UI",12),height=36,
                     corner_radius=6).pack(fill="x",pady=(2,0))
        self.steam_frame=ctk.CTkFrame(cf,fg_color="transparent")
        self.steam_frame.pack(fill="x",padx=12,pady=(8,0))
        ctk.CTkLabel(self.steam_frame,text="Steam ID",font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["text"],anchor="w").pack(anchor="w")
        self.steam_var=ctk.StringVar(value=self.cfg.get("steam_id",""))
        ctk.CTkEntry(self.steam_frame,textvariable=self.steam_var,fg_color=C["card2"],
                     border_color=C["border"],text_color=C["text"],font=ctk.CTkFont("Segoe UI",12),
                     height=36,corner_radius=6).pack(fill="x",pady=(2,4))
        ctk.CTkLabel(self.steam_frame,
                     text="steamcommunity.com → your profile → number in URL",
                     font=ctk.CTkFont("Segoe UI",10),text_color=C["muted"],anchor="w").pack(anchor="w")
        ctk.CTkLabel(cf,text="Shared Cloud Folder",font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["text"],anchor="w").pack(anchor="w",padx=12,pady=(10,0))
        dr=ctk.CTkFrame(cf,fg_color="transparent"); dr.pack(fill="x",padx=12,pady=(2,0))
        self.drive_var=ctk.StringVar(value=self.cfg.get("drive_folder",""))
        ctk.CTkEntry(dr,textvariable=self.drive_var,fg_color=C["card2"],border_color=C["border"],
                     text_color=C["text"],font=ctk.CTkFont("Segoe UI",12),height=36,
                     corner_radius=6).pack(side="left",fill="x",expand=True)
        ctk.CTkButton(dr,text="Browse",width=80,height=36,fg_color=C["accent"],
                      hover_color=C["accent2"],font=ctk.CTkFont("Segoe UI",12),corner_radius=6,
                      command=self._browse_drive).pack(side="left",padx=(6,0))
        ctk.CTkButton(cf,text="Save Configuration",height=38,fg_color=C["accent"],
                      hover_color=C["accent2"],font=ctk.CTkFont("Segoe UI",13,"bold"),
                      corner_radius=8,command=self._save_cfg).pack(fill="x",padx=12,pady=(10,14))

    def _build_worlds_card(self):
        wf=self._card()
        wfh=ctk.CTkFrame(wf,fg_color="transparent"); wfh.pack(fill="x",padx=12,pady=(10,4))
        ctk.CTkLabel(wfh,text="WORLDS",font=ctk.CTkFont("Segoe UI",11,"bold"),
                     text_color=C["muted"]).pack(side="left")
        ctk.CTkButton(wfh,text="↻",width=32,height=28,fg_color=C["blue"],
                      hover_color=C["blue2"],font=ctk.CTkFont("Segoe UI",13),
                      corner_radius=6,command=self._force_full_scan).pack(side="right")
        ctk.CTkLabel(wf,text="⚠  Check with your group before loading a shared world.",
                     font=ctk.CTkFont("Segoe UI",10),text_color=C["amber"],
                     fg_color=C["card2"],corner_radius=6).pack(fill="x",padx=12,pady=(0,6))
        self.world_frame=ctk.CTkFrame(wf,fg_color="transparent")
        self.world_frame.pack(fill="x",padx=8,pady=(0,10))

    def _build_sync_card(self):
        pf=self._card()
        self.sync_btn=ctk.CTkButton(pf,text="⟳   SYNC NOW",height=52,
            fg_color=C["accent"],hover_color=C["accent2"],
            font=ctk.CTkFont("Segoe UI",16,"bold"),corner_radius=10,command=self._sync_now)
        self.sync_btn.pack(fill="x",padx=12,pady=(12,6))
        self.sync_status=ctk.CTkLabel(pf,
            text="Syncs all available updates — launch your game however you normally would",
            font=ctk.CTkFont("Segoe UI",11),text_color=C["muted"])
        self.sync_status.pack(pady=(0,12))

    def _build_log_card(self):
        lf=self._card("ACTIVITY LOG")
        log_hdr=ctk.CTkFrame(lf,fg_color="transparent"); log_hdr.pack(fill="x",padx=12,pady=(4,0))
        ctk.CTkButton(log_hdr,text="Clear Log",width=70,height=22,
            fg_color=C["card2"],hover_color=C["border"],text_color=C["muted"],
            font=ctk.CTkFont("Segoe UI",10),corner_radius=4,
            command=self._clear_log).pack(side="right")
        self.log_box=ctk.CTkTextbox(lf,height=130,fg_color=C["bg"],text_color="#8899aa",
                                     font=ctk.CTkFont("Consolas",11),corner_radius=6,
                                     border_width=0,state="disabled")
        self.log_box.pack(fill="x",padx=12,pady=(4,12))

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0","end")
        self.log_box.configure(state="disabled")

    def _dismiss_fund_banner(self):
        self.cfg["fund_banner_dismissed"] = True
        save_config(self.cfg)
        if hasattr(self,"_fund_banner_frame"):
            self._fund_banner_frame.destroy()

    # ── Add Game (smart scan) ─────────────────────────────────────────────────
    def _show_add_game(self):
        """Scan known save locations and let user add a detected or custom game."""
        win=ctk.CTkToplevel(self); win.title("Add Game")
        win.geometry("500x560"); win.configure(fg_color=C["bg"])
        win.grab_set(); win.resizable(False,False)
        ctk.CTkFrame(win,fg_color=C["accent"],height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,text="Add a Game",font=ctk.CTkFont("Segoe UI",16,"bold"),
                     text_color=C["text"]).pack(pady=(16,4))
        ctk.CTkLabel(win,text="Hearth scanned your PC for game save folders.",
                     font=ctk.CTkFont("Segoe UI",11),text_color=C["muted"]).pack(pady=(0,10))

        detected = self._scan_for_games()
        existing = set(GAMES.keys()) | set(self.cfg.get("custom_games",{}).keys())

        list_frame = ctk.CTkScrollableFrame(win,fg_color=C["card"],corner_radius=8,height=260)
        list_frame.pack(fill="x",padx=20,pady=(0,10))

        selected_game = {"name":"","path":"","ext":""}

        if detected:
            for gname, gpath, gext in detected:
                if gname in existing: continue
                row=ctk.CTkFrame(list_frame,fg_color="transparent")
                row.pack(fill="x",padx=8,pady=3)
                def _pick(n=gname,p=str(gpath),e=gext):
                    selected_game["name"]=n; selected_game["path"]=p; selected_game["ext"]=e
                    name_e.delete(0,"end"); name_e.insert(0,n)
                    path_e.delete(0,"end"); path_e.insert(0,p)
                    ext_e.delete(0,"end"); ext_e.insert(0,e)
                ctk.CTkButton(row,text=gname,anchor="w",fg_color=C["card2"],
                    hover_color=C["border"],text_color=C["text"],
                    font=ctk.CTkFont("Segoe UI",11),height=28,corner_radius=4,
                    command=_pick).pack(side="left",fill="x",expand=True)
                ctk.CTkLabel(row,text=gext,font=ctk.CTkFont("Segoe UI",10),
                             text_color=C["muted"],width=60).pack(side="left",padx=4)
        else:
            ctk.CTkLabel(list_frame,text="No new games detected. Add one manually below.",
                font=ctk.CTkFont("Segoe UI",11),text_color=C["muted"]).pack(pady=16)

        # Manual entry
        card=ctk.CTkFrame(win,fg_color=C["card"],corner_radius=8)
        card.pack(fill="x",padx=20,pady=(0,10))
        ctk.CTkLabel(card,text="Game name",font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["muted"],anchor="w").pack(fill="x",padx=12,pady=(10,0))
        name_e=ctk.CTkEntry(card,fg_color=C["card2"],border_color=C["border"],
            text_color=C["text"],font=ctk.CTkFont("Segoe UI",11),height=32,corner_radius=6)
        name_e.pack(fill="x",padx=12,pady=(2,6))
        ctk.CTkLabel(card,text="Save folder",font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["muted"],anchor="w").pack(fill="x",padx=12,pady=(0,0))
        pr=ctk.CTkFrame(card,fg_color="transparent"); pr.pack(fill="x",padx=12,pady=(2,6))
        path_e=ctk.CTkEntry(pr,fg_color=C["card2"],border_color=C["border"],
            text_color=C["text"],font=ctk.CTkFont("Segoe UI",11),height=32,corner_radius=6)
        path_e.pack(side="left",fill="x",expand=True)
        ctk.CTkButton(pr,text="Browse",width=70,height=32,fg_color=C["accent"],
            hover_color=C["accent2"],font=ctk.CTkFont("Segoe UI",10),corner_radius=6,
            command=lambda:(path_e.delete(0,"end"),
                path_e.insert(0,filedialog.askdirectory(title="Select Save Folder") or ""))
            ).pack(side="left",padx=(6,0))
        ctk.CTkLabel(card,text="File extension (e.g. .sav)",font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["muted"],anchor="w").pack(fill="x",padx=12,pady=(0,0))
        ext_e=ctk.CTkEntry(card,fg_color=C["card2"],border_color=C["border"],
            text_color=C["text"],font=ctk.CTkFont("Segoe UI",11),height=32,corner_radius=6)
        ext_e.pack(fill="x",padx=12,pady=(2,10))

        def _add():
            n=name_e.get().strip(); p=path_e.get().strip(); e=ext_e.get().strip()
            if not n: messagebox.showerror("Hearth","Enter a game name.",parent=win); return
            if not p or not Path(p).exists(): messagebox.showerror("Hearth","Select a valid save folder.",parent=win); return
            if not e.startswith("."): e="."+e
            cg=self.cfg.get("custom_games",{})
            cg[n]={"path":p,"ext":e}
            self.cfg["custom_games"]=cg; save_config(self.cfg)
            self._log(f"➕ Added game: {n}"); win.destroy(); self._force_full_scan()

        ctk.CTkButton(win,text="Add Game",height=40,fg_color=C["accent"],hover_color=C["accent2"],
            font=ctk.CTkFont("Segoe UI",13,"bold"),corner_radius=8,command=_add).pack(
            fill="x",padx=20,pady=(0,16))

    def _scan_for_games(self):
        """Scan known save roots for folders containing game-like save files."""
        results=[]
        seen=set()
        for root in SCAN_ROOTS:
            try:
                rp=root.resolve()
                if not rp.exists(): continue
                for child in rp.iterdir():
                    if not child.is_dir(): continue
                    name=child.name
                    if name.lower() in ("microsoft","windows","temp","cache","logs",
                                        "roaming","local","locallow","appdata"): continue
                    if name in seen: continue
                    # Look for save-like files one level deep
                    exts_found=set()
                    try:
                        for f in child.iterdir():
                            if f.is_file() and f.suffix.lower() in GAME_SAVE_EXTENSIONS:
                                if f.suffix.lower() not in GENERIC_EXTENSIONS:
                                    exts_found.add(f.suffix.lower())
                                else:
                                    # Generic ext — only count if folder name looks like a game
                                    if any(c.isupper() for c in name) or " " in name:
                                        exts_found.add(f.suffix.lower())
                    except PermissionError: continue
                    if exts_found:
                        ext=sorted(exts_found)[0]
                        results.append((name, child, ext))
                        seen.add(name)
            except (PermissionError, OSError): continue
        return sorted(results, key=lambda x: x[0].lower())

    # ── Hide/Show game filter ─────────────────────────────────────────────────
    def _show_game_filter(self):
        """Menu: checklist of all known games — check to show, uncheck to hide."""
        all_games = list(GAMES.keys()) + list(self.cfg.get("custom_games",{}).keys())
        hidden = set(self.cfg.get("hidden_games",[]))
        win=ctk.CTkToplevel(self); win.title("Show / Hide Games")
        win.geometry("340x480"); win.configure(fg_color=C["bg"])
        win.grab_set(); win.resizable(False,False)
        ctk.CTkFrame(win,fg_color=C["accent"],height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,text="Show / Hide Games",font=ctk.CTkFont("Segoe UI",15,"bold"),
                     text_color=C["text"]).pack(pady=(14,6))
        ctk.CTkLabel(win,text="Uncheck games you don't play to hide them from the list.",
                     font=ctk.CTkFont("Segoe UI",10),text_color=C["muted"],
                     wraplength=280).pack(pady=(0,8))
        sf=ctk.CTkScrollableFrame(win,fg_color=C["card"],corner_radius=8,height=300)
        sf.pack(fill="x",padx=20,pady=(0,10))
        vars_map={}
        for gk in all_games:
            if gk=="Custom Game": continue
            var=ctk.BooleanVar(value=gk not in hidden)
            vars_map[gk]=var
            ctk.CTkCheckBox(sf,text=gk,variable=var,
                fg_color=C["accent"],hover_color=C["accent2"],
                border_color=C["border"],checkmark_color="white",
                font=ctk.CTkFont("Segoe UI",11)).pack(anchor="w",padx=12,pady=4)
        def _save_filter():
            new_hidden=[gk for gk,v in vars_map.items() if not v.get()]
            self.cfg["hidden_games"]=new_hidden; save_config(self.cfg)
            win.destroy(); self._force_full_scan()
        ctk.CTkButton(win,text="Save",height=38,fg_color=C["accent"],hover_color=C["accent2"],
            font=ctk.CTkFont("Segoe UI",12,"bold"),corner_radius=8,
            command=_save_filter).pack(fill="x",padx=20,pady=(0,14))

    # ── Field helpers ─────────────────────────────────────────────────────────
    def _load_fields(self):
        self.username_var.set(self.cfg.get("username",""))
        self.steam_var.set(self.cfg.get("steam_id",""))
        self.drive_var.set(self.cfg.get("drive_folder",""))

    def _browse_drive(self):
        f=filedialog.askdirectory(title="Select Shared Cloud Folder")
        if f: self.drive_var.set(f)

    def _browse_save_manual(self):
        f=filedialog.askdirectory(title="Select Game Save Folder")
        if not f: return
        choices="\n".join(GAMES.keys())
        game=simpledialog.askstring("Which Game?",f"Enter game name exactly:\n{choices}",parent=self)
        if game and game in GAMES:
            if "custom_paths" not in self.cfg: self.cfg["custom_paths"]={}
            self.cfg["custom_paths"][game]=f; save_config(self.cfg)
            self._log(f"Custom path set for {game}"); self._scan_all_worlds()

    def _save_cfg(self):
        self.cfg["username"]=self.username_var.get().strip()
        self.cfg["steam_id"]=self.steam_var.get().strip()
        self.cfg["drive_folder"]=self.drive_var.get().strip()
        self.cfg["shared_worlds"]=self.shared_worlds
        self.cfg["world_labels"]=self.world_labels
        self.cfg["collapsed_games"]=list(self._collapsed_games)
        save_config(self.cfg); self._log("Configuration saved.")
        self._scan_all_worlds(); messagebox.showinfo("Hearth","Configuration saved!")

    # ── World scanning — stable widget approach (no flash) ───────────────────
    def _collect_world_data(self):
        """Collect all world data without touching UI. Returns structured list."""
        drive=self.cfg.get("drive_folder","")
        username=self.username_var.get() or self.cfg.get("username","")
        rows=[]
        hidden=set(self.cfg.get("hidden_games",[]))
        for gk in list(GAMES.keys()):
            if gk=="Custom Game": continue
            if gk in hidden: continue
            my=get_local_worlds(gk,self.cfg)
            all_shared=get_all_shared_worlds(drive,gk) if drive and Path(drive).exists() else []
            others={}
            for e in all_shared:
                if e["owner"]!=username: others.setdefault(e["owner"],[]).append(e)
            info=GAMES.get(gk,{})
            # For Steam Cloud games with no local saves, always show the warning
            # even if there are no shared worlds either
            steam_cloud_problem = info.get("steam_cloud") and not my and not find_save_folder(gk,self.cfg)
            # Valheim-specific: show a clear message if no save folder found at all
            valheim_missing = (gk=="Valheim" and not my and not find_save_folder(gk,self.cfg) and not steam_cloud_problem)
            if not my and not others and not steam_cloud_problem and not valheim_missing: continue
            rows.append({"type":"game_header","game":gk})
            if valheim_missing:
                rows.append({"type":"cloud_warning","game":gk,
                    "msg":"No Valheim save folder found. If you've played Valheim, your worlds may be stored "
                          "in Steam Cloud.\nFix: Steam → right-click Valheim → Properties → General → uncheck "
                          "'Keep game saves in the Steam Cloud'\nThen launch Valheim, load into a world, exit, "
                          "and Hearth will find it."})
                continue
            if steam_cloud_problem:
                rows.append({"type":"cloud_warning","game":gk,
                    "msg":f"No save files found for {gk}. If you've played this game, Steam Cloud is likely enabled.\n"
                          f"Fix: Steam → right-click {gk} → Properties → General → uncheck 'Keep game saves in the Steam Cloud'\n"
                          f"Then launch the game once to create a local save file."})
                if others:
                    for owner,entries in others.items():
                        rows.append({"type":"section","text":f"{owner.upper()}'S WORLDS"})
                        for e in entries:
                            st,sc=self._world_status(drive,gk,e["owner"],e["world_id"],username,e["lock"],None,False,True)
                            rows.append({"type":"world","key":(gk,e["owner"],e["world_id"]),
                                "game":gk,"owner":e["owner"],"world_id":e["world_id"],
                                "display":e["display_name"],"is_mine":False,"shared":True,
                                "status":st,"status_color":sc,"mtime":"","file":None,
                                "lock":e.get("lock"),"world_entry":e})
                continue
            if my:
                rows.append({"type":"section","text":"YOUR WORLDS"})
                for we in my:
                    shared=self.shared_worlds.get(gk,{}).get(we["name"],False)
                    disp=self.world_labels.get(we.get("hex_id",""),we.get("display",we["name"]))
                    st,sc=self._world_status(drive,gk,username,we["name"],username,None,we.get("file"),True,shared)
                    fp=we.get("file")
                    mtime=""
                    if fp and Path(str(fp)).exists():
                        mtime=datetime.fromtimestamp(Path(str(fp)).stat().st_mtime).strftime("%m/%d %H:%M")
                    rows.append({"type":"world","key":(gk,username,we["name"]),
                        "game":gk,"owner":username,"world_id":we["name"],"display":disp,
                        "is_mine":True,"shared":shared,"status":st,"status_color":sc,
                        "mtime":mtime,"file":fp,"world_entry":we})
            for owner,entries in others.items():
                rows.append({"type":"section","text":f"{owner.upper()}'S WORLDS"})
                for e in entries:
                    fp=None  # others don't have local file initially
                    # Check if we have a local copy
                    local_candidates=get_local_worlds(gk,self.cfg)
                    for lw in local_candidates:
                        if lw["name"]==e["world_id"]: fp=lw.get("file"); break
                    st,sc=self._world_status(drive,gk,e["owner"],e["world_id"],username,
                                              e["lock"],fp,False,True)
                    mtime=""
                    if fp and Path(str(fp)).exists():
                        mtime=datetime.fromtimestamp(Path(str(fp)).stat().st_mtime).strftime("%m/%d %H:%M")
                    rows.append({"type":"world","key":(gk,e["owner"],e["world_id"]),
                        "game":gk,"owner":e["owner"],"world_id":e["world_id"],
                        "display":e["display_name"],"is_mine":False,"shared":True,
                        "status":st,"status_color":sc,"mtime":mtime,"file":fp,
                        "lock":e.get("lock"),"world_entry":e})
        custom=get_local_worlds("Custom Game",self.cfg)
        if custom:
            rows.append({"type":"game_header","game":"Custom Game"})
            rows.append({"type":"section","text":"YOUR WORLDS"})
            for we in custom:
                shared=self.shared_worlds.get("Custom Game",{}).get(we["name"],False)
                st,sc=self._world_status(drive,"Custom Game",username,we["name"],username,None,we.get("file"),True,shared)
                fp=we.get("file"); mtime=""
                if fp and Path(str(fp)).exists():
                    mtime=datetime.fromtimestamp(Path(str(fp)).stat().st_mtime).strftime("%m/%d %H:%M")
                rows.append({"type":"world","key":("Custom Game",username,we["name"]),
                    "game":"Custom Game","owner":username,"world_id":we["name"],
                    "display":we["name"],"is_mine":True,"shared":shared,
                    "status":st,"status_color":sc,"mtime":mtime,"file":fp,"world_entry":we})

        # ── User-added games (via Add Game) ───────────────────────────────────
        hidden = set(self.cfg.get("hidden_games",[]))
        for gname, ginfo in self.cfg.get("custom_games",{}).items():
            if gname in hidden: continue
            gpath = Path(ginfo.get("path",""))
            gext  = ginfo.get("ext","")
            if not gpath.exists(): continue
            worlds = []
            try:
                for f in gpath.iterdir():
                    if f.is_file() and f.suffix.lower()==gext.lower() and "_backup" not in f.name:
                        worlds.append({"name":f.stem,"file":f,"display":f.stem,"slot":None})
            except: pass
            if not worlds: continue
            rows.append({"type":"game_header","game":gname})
            rows.append({"type":"section","text":"YOUR WORLDS"})
            for we in sorted(worlds,key=lambda x:x["name"].lower()):
                shared=self.shared_worlds.get(gname,{}).get(we["name"],False)
                st,sc=self._world_status(drive,gname,username,we["name"],username,None,we.get("file"),True,shared)
                fp=we.get("file"); mtime=""
                if fp and Path(str(fp)).exists():
                    mtime=datetime.fromtimestamp(Path(str(fp)).stat().st_mtime).strftime("%m/%d %H:%M")
                rows.append({"type":"world","key":(gname,username,we["name"]),
                    "game":gname,"owner":username,"world_id":we["name"],
                    "display":we["name"],"is_mine":True,"shared":shared,
                    "status":st,"status_color":sc,"mtime":mtime,"file":fp,"world_entry":we})

        if not rows:
            rows.append({"type":"empty"})
        return rows, username, drive

    def _force_full_scan(self):
        """Force a full rebuild of the world list (refresh button)."""
        self._last_scan_hash=""
        self._scan_all_worlds()

    def _scan_all_worlds(self):
        """Smart scan — full rebuild only when structure changes, status update otherwise."""
        rows,username,drive=self._collect_world_data()
        # Build a hash of the structure (keys and order) to detect structural changes
        struct_keys=[r.get("key",r.get("type","")) for r in rows]
        struct_hash=str(struct_keys)
        if struct_hash!=self._last_scan_hash:
            # Structure changed — full rebuild needed
            self._last_scan_hash=struct_hash
            self._full_rebuild(rows,username,drive)
        else:
            # Structure same — just update status labels in place (NO FLASH)
            self._update_statuses_inplace(rows)
        self.after(15000,self._scan_all_worlds)

    def _toggle_game_collapse(self, game, btn):
        """Show/hide a game's child container — no rebuild, no flash, order preserved."""
        container = self._game_children.get(game)
        if not container:
            return
        if game in self._collapsed_games:
            self._collapsed_games.discard(game)
            btn.configure(text="▼")
            container.pack(fill="x")
        else:
            self._collapsed_games.add(game)
            btn.configure(text="▶")
            container.pack_forget()
        self.cfg["collapsed_games"] = list(self._collapsed_games)
        save_config(self.cfg)

    def _full_rebuild(self,rows,username,drive):
        """Full widget rebuild — only called when world list structure changes."""
        # Clear existing widgets and widget dicts
        for w in self.world_frame.winfo_children(): w.destroy()
        self._world_widgets={}
        self._game_children={}   # game -> container frame holding all child widgets
        current_game=None
        current_container=None
        for row in rows:
            t=row["type"]
            if t=="game_header":
                gk=row["game"]
                current_game=gk
                collapsed = gk in self._collapsed_games
                # Outer wrapper keeps header + children together in pack order
                outer=ctk.CTkFrame(self.world_frame,fg_color="transparent")
                outer.pack(fill="x",pady=(4,0))
                sh=ctk.CTkFrame(outer,fg_color=C["card2"],corner_radius=8)
                sh.pack(fill="x",pady=(0,2))
                toggle_btn=ctk.CTkButton(sh,text="▶" if collapsed else "▼",width=28,height=22,
                    font=ctk.CTkFont("Segoe UI",11),
                    fg_color="transparent",hover_color=C["border"],text_color=C["muted"],
                    corner_radius=4)
                toggle_btn.configure(command=lambda g=gk,b=toggle_btn: self._toggle_game_collapse(g,b))
                toggle_btn.pack(side="left",padx=(6,0),pady=6)
                ctk.CTkLabel(sh,text=gk,font=ctk.CTkFont("Segoe UI",11,"bold"),
                             text_color=C["accent"]).pack(side="left",padx=4,pady=6)
                # World count badge — visible when collapsed
                game_worlds=[r for r in rows if r.get("type")=="world" and r.get("game")==gk]
                shared_count=sum(1 for r in game_worlds if r.get("shared"))
                if game_worlds:
                    badge_text=f"{len(game_worlds)} world{'s' if len(game_worlds)!=1 else ''}"
                    if shared_count: badge_text+=f"  •  {shared_count} shared"
                    ctk.CTkLabel(sh,text=badge_text,font=ctk.CTkFont("Segoe UI",9),
                                 text_color=C["muted"]).pack(side="left",padx=(4,0),pady=6)
                if GAMES.get(gk,{}).get("verified")==False:
                    ctk.CTkLabel(sh,text="unverified",font=ctk.CTkFont("Segoe UI",10),
                                 text_color=C["muted"]).pack(side="right",padx=(0,10))
                ctk.CTkButton(sh,text="Config",width=60,height=22,
                    font=ctk.CTkFont("Segoe UI",10),
                    fg_color=C["card"],hover_color=C["border"],text_color=C["muted"],
                    corner_radius=4,
                    command=lambda g=gk: self._config_game_path(g)).pack(side="right",padx=(0,8),pady=4)
                # Container for all child rows — this is what gets hidden on collapse
                current_container=ctk.CTkFrame(outer,fg_color="transparent")
                self._game_children[gk]=current_container
                if collapsed:
                    pass  # don't pack — stays hidden
                else:
                    current_container.pack(fill="x")
            elif t=="section":
                lbl=ctk.CTkLabel(current_container,text=f"  {row['text']}",
                    font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=C["muted"])
                lbl.pack(anchor="w",padx=8,pady=(4,0))
            elif t=="cloud_warning":
                lbl=ctk.CTkLabel(current_container,text=f"  ⚠  {row['msg']}",
                    font=ctk.CTkFont("Segoe UI",10),text_color=C["amber"],wraplength=500)
                lbl.pack(anchor="w",padx=8,pady=4)
            elif t=="empty":
                ctk.CTkLabel(self.world_frame,text="No worlds found. Launch your game once and close it — Hearth will find your saves automatically.",
                    font=ctk.CTkFont("Segoe UI",11),text_color=C["muted"]).pack(pady=8,padx=8)
            elif t=="world":
                key=row["key"]
                r=ctk.CTkFrame(current_container,fg_color=C["surface"],corner_radius=8)
                r.pack(fill="x",pady=2,padx=4)
                if row["is_mine"]:
                    var=ctk.BooleanVar(value=row["shared"])
                    we=row.get("world_entry")
                    ctk.CTkCheckBox(r,variable=var,text="",width=20,height=20,
                        fg_color=C["accent"],hover_color=C["accent2"],
                        border_color=C["border"],checkmark_color="white",
                        command=lambda n=row["world_id"],v=var,g=row["game"],x=we:
                            self._toggle_share(g,n,v,x)).pack(side="left",padx=(10,4),pady=10)
                else:
                    # Per-world participation toggle for others' worlds — default OFF
                    gk=row["game"]; wid=row["world_id"]
                    participated=self.participated_worlds.get(gk,{}).get(wid,False)
                    pvar=ctk.BooleanVar(value=participated)
                    def _toggle_participation(g=gk,w=wid,v=pvar):
                        if g not in self.participated_worlds: self.participated_worlds[g]={}
                        self.participated_worlds[g][w]=v.get()
                        self.cfg["participated_worlds"]=self.participated_worlds; save_config(self.cfg)
                        state="Participating" if v.get() else "Not participating"
                        self._log(f"{state}: {w} ({g})")
                    ctk.CTkCheckBox(r,variable=pvar,text="",width=20,height=20,
                        fg_color=C["accent2"],hover_color=C["accent"],
                        border_color=C["border"],checkmark_color="white",
                        command=_toggle_participation).pack(side="left",padx=(10,4),pady=10)
                ctk.CTkLabel(r,text=row["display"],font=ctk.CTkFont("Segoe UI",12,"bold"),
                             text_color=C["text"]).pack(side="left",padx=(4,12))
                st=row["status"]; sc=row["status_color"]
                slbl=ctk.CTkLabel(r,text=st,font=ctk.CTkFont("Segoe UI",10),text_color=sc)
                slbl.pack(side="left")
                we=row.get("world_entry")
                if "download" in st.lower() or "available" in st.lower():
                    slbl.configure(cursor="hand2")
                    slbl.bind("<Button-1>",lambda e,g=row["game"],o=row["owner"],x=we:self._quick_pull(g,o,x))
                mtime_lbl=ctk.CTkLabel(r,text=f"Last played: {row['mtime']}" if row["mtime"] else ("Not downloaded yet" if not row["is_mine"] else ""),
                    font=ctk.CTkFont("Segoe UI",10),text_color=C["muted"])
                mtime_lbl.pack(side="right",padx=12)
                self._world_widgets[key]=(r,slbl,mtime_lbl,row.get("world_entry"))

    def _update_statuses_inplace(self,rows):
        """Update only status labels — no widget creation or destruction. Zero flash."""
        for row in rows:
            if row["type"]!="world": continue
            key=row["key"]
            if key not in self._world_widgets: continue
            _,slbl,mtime_lbl,we=self._world_widgets[key]
            st=row["status"]; sc=row["status_color"]
            try:
                slbl.configure(text=st,text_color=sc)
                # Update click binding based on new status
                if "download" in st.lower() or "available" in st.lower():
                    slbl.configure(cursor="hand2")
                    slbl.bind("<Button-1>",lambda e,g=row["game"],o=row["owner"],x=we:self._quick_pull(g,o,x))
                else:
                    slbl.configure(cursor="")
                    slbl.unbind("<Button-1>")
                if row["mtime"]:
                    mtime_lbl.configure(text=f"Last played: {row['mtime']}")
            except Exception:
                pass  # Widget was destroyed, will rebuild next cycle

    def _world_status(self,drive,gk,owner,world_id,username,lock,file_path,is_mine,shared):
        if is_mine and not shared: return "● Not shared",C["muted"]
        if lock:
            who=lock.get("user","?")
            return ("🎮 You are hosting",C["green"]) if who==username else (f"🔒 {who} is hosting",C["amber"])
        if not is_mine:
            participated=self.participated_worlds.get(gk,{}).get(world_id,False)
            if not participated:
                return "☁ Available — check box to participate",C["muted"]
            if file_path and Path(str(file_path)).exists():
                try:
                    newer=is_drive_newer(drive,gk,owner,world_id,self.cfg)
                except: newer=False
                return ("⬇ Update available — click to download",C["sky"]) if newer else ("✅ Downloaded",C["green"])
            return "⬇ Available to download — click to download",C["sky"]
        if drive and Path(drive).exists():
            wf=Path(drive)/gk/owner/str(world_id)
            if wf.exists():
                files=[f for f in wf.iterdir() if f.name not in (LOCK_FILENAME,META_FILENAME,MAP_FILENAME,LOG_FILENAME)]
                if files:
                    try:
                        # Use hash check — same logic as auto-pull so status matches behavior
                        newer=is_drive_newer(drive,gk,owner,world_id,self.cfg)
                        if newer:
                            return "⬇ Update available",C["sky"]
                        return "✅ Synced with cloud",C["green"]
                    except: return "✅ Synced with cloud",C["green"]
            return "● Not yet pushed",C["amber"]
        return "● Not shared",C["muted"]

    def _config_game_path(self, game_key):
        """Let user override the save path for a specific game."""
        current = self.cfg.get("custom_paths", {}).get(game_key, "")
        folder = filedialog.askdirectory(
            title=f"Select save folder for {game_key}",
            initialdir=current if current and Path(current).exists() else str(Path.home())
        )
        if folder:
            if "custom_paths" not in self.cfg:
                self.cfg["custom_paths"] = {}
            self.cfg["custom_paths"][game_key] = folder
            save_config(self.cfg)
            self._log(f"📁 Save path updated for {game_key}")
            self._scan_all_worlds()
        elif current:
            # Offer to clear the override
            if messagebox.askyesno("Hearth", f"Clear custom path for {game_key} and use default?"):
                self.cfg.get("custom_paths", {}).pop(game_key, None)
                save_config(self.cfg)
                self._log(f"📁 Save path reset to default for {game_key}")
                self._scan_all_worlds()

    def _quick_pull(self, gk, owner, world_entry):
        drive = self.cfg.get("drive_folder","")
        if not drive or not world_entry: return
        # Guard against double-pull if user clicks rapidly
        key = (gk, owner, world_entry.get("world_id",""))
        if getattr(self, "_pulling", set()) and key in self._pulling:
            return
        if not hasattr(self, "_pulling"): self._pulling = set()
        self._pulling.add(key)
        display = world_entry.get("display_name", world_entry.get("world_id",""))
        self._log(f"⬇ Downloading: {display}...")
        def do_pull():
            try:
                ok, reason = pull_world(drive, gk, owner, world_entry, self.cfg, is_own=False)
                def done():
                    self._pulling.discard(key)
                    if ok:
                        self._log(f"⬇ Downloaded: {display}")
                        self._force_full_scan()
                    else:
                        friendly = {
                            "no_remote":      f"⚠ {display} — world not found in Drive. The owner may not have shared it yet.",
                            "no_local_path":  f"⚠ {display} — can't find your local save folder. Launch the game once and try again.",
                            "no_files_copied":f"⚠ {display} — no files were downloaded. The Drive folder may be empty or still syncing.",
                            "bad_world_id":   f"⚠ {display} — world ID is missing. Try refreshing.",
                            "no_free_slot":   f"⚠ {display} — no free save slot available. You may need to delete a world in-game first.",
                        }.get(reason, f"⚠ {display} — download failed: {reason}")
                        self._log(friendly)
                self.after(0, done)
            except Exception as e:
                self.after(0, lambda: self._pulling.discard(key))
                self.after(0, lambda: self._log(f"⚠ {display} — unexpected error: {e}. Check your Drive connection."))
        threading.Thread(target=do_pull, daemon=True).start()

    def _toggle_share(self,gk,world_id,var,world_entry=None):
        drive=self.cfg.get("drive_folder",""); username=self.cfg.get("username","")
        info=GAMES.get(gk,{})
        if gk not in self.shared_worlds: self.shared_worlds[gk]={}
        if var.get() and not self.first_share_shown:
            messagebox.showinfo("Hearth — World Naming Rule",
                "Before sharing, make sure nobody in your group has a world with the same name.\n\n"
                "Hearth identifies worlds by name. Duplicate names cause sync conflicts.\n\n"
                "You can rename worlds inside the game before sharing.")
            self.first_share_shown=True; self.cfg["first_share_shown"]=True
        # Validate world name for illegal characters or leading/trailing spaces
        if var.get():
            import re
            illegal=re.compile(r'[\\/:*?"<>|]')
            if world_id != world_id.strip() or illegal.search(world_id):
                problem="leading/trailing spaces" if world_id != world_id.strip() else "special characters"
                messagebox.showwarning("Hearth — World Name Issue",
                    f"The world name '{world_id}' has {problem} which can cause sync errors.\n\n"
                    f"Please rename this world in-game to remove any spaces at the start or end "
                    f"and avoid these characters: \\ / : * ? \" < > |\n\n"
                    f"Then try sharing again.")
                var.set(False); return
        display_name=world_id
        if var.get() and info.get("slot_type")=="hex" and world_entry:
            hex_id=world_entry.get("hex_id",""); existing=self.world_labels.get(hex_id,"")
            label=simpledialog.askstring("Name This World",
                "What would you like to call this world?\n(Display name in Hearth only)",
                initialvalue=existing or f"World {ENSHROUDED_HEX_TO_SLOT.get(hex_id,0)+1}",parent=self)
            if label:
                self.world_labels[hex_id]=label.strip()
                self.cfg["world_labels"]=self.world_labels; display_name=label.strip()
        self.shared_worlds[gk][world_id]=var.get()
        self.cfg["shared_worlds"]=self.shared_worlds; save_config(self.cfg)
        if var.get() and drive and username:
            if world_entry:
                push_world(drive,gk,username,world_entry,self.cfg,display_name)
                self._log(f"⬆ Shared and pushed: {display_name}")
            else:
                self._log(f"⚠ Shared: {display_name} — world entry missing, push skipped. Reopen Hearth to push.")
        else: self._log(f"Unshared: {world_id}")

    # ── Sync Now ──────────────────────────────────────────────────────────────
    def _sync_now(self):
        if self._syncing: return
        self._syncing=True
        self._set_tray_icon("syncing")
        self.sync_btn.configure(text="⟳   Syncing...",state="disabled")
        self.sync_status.configure(text="Checking for updates...",text_color=C["amber"])
        def do_sync():
            drive=self.cfg.get("drive_folder",""); username=self.cfg.get("username","")
            pulled=0; pushed=0
            if drive and username:
                # Pull others' worlds that are newer
                for gk in GAMES:
                    for entry in get_all_shared_worlds(drive,gk):
                        if entry["owner"]==username or entry["lock"]: continue
                        try:
                            if is_drive_newer(drive,gk,entry["owner"],entry["world_id"],self.cfg):
                                ok,reason=pull_world(drive,gk,entry["owner"],entry,self.cfg,is_own=False)
                                if ok:
                                    self._log(f"⬇ Synced: {entry['display_name']}"); pulled+=1
                                else:
                                    friendly = {
                                        "no_remote":      f"not found in Drive — may still be uploading",
                                        "no_local_path":  f"can't find local save folder — launch the game once",
                                        "no_files_copied":f"Drive folder empty or still syncing",
                                        "no_free_slot":   f"no free save slot — delete a world in-game first",
                                    }.get(reason, reason)
                                    self._log(f"⚠ Skipped {entry['display_name']}: {friendly}")
                        except Exception as e:
                            self._log(f"⚠ Skipped {entry['display_name']}: unexpected error — {e}")
            def done():
                self._syncing=False
                self.sync_btn.configure(text="⟳   SYNC NOW",state="normal")
                if pulled>0:
                    self.sync_status.configure(text=f"✅ Sync complete — {pulled} updated",text_color=C["green"])
                    self._set_tray_icon("nominal")
                else:
                    self.sync_status.configure(text="✅ Everything is up to date",text_color=C["green"])
                    self._set_tray_icon("nominal")
                self._scan_all_worlds()  # Force full UI refresh after sync
                self.after(5000,lambda:self.sync_status.configure(
                    text="Syncs all available updates — launch your game however you normally would",text_color=C["muted"]))
            self.after(0,done)
        threading.Thread(target=do_sync,daemon=True).start()

    # ── Advanced ──────────────────────────────────────────────────────────────
    def _manual_unlock(self):
        drive=self.cfg.get("drive_folder",""); username=self.cfg.get("username","")
        locked=[]
        for gk in GAMES:
            for entry in get_all_shared_worlds(drive,gk):
                if entry["lock"]: locked.append(entry)
        if not locked: messagebox.showinfo("Hearth","No worlds are currently locked."); return
        names="\n".join(f"{e['owner']} / {e['display_name']}" for e in locked)
        if messagebox.askyesno("Hearth",f"Unlock these worlds?\n\n{names}"):
            for entry in locked:
                _clear_lock(entry["folder"]); self._log(f"🔓 Unlocked: {entry['display_name']}")
            self._scan_all_worlds()

    def _open_backups(self):
        if BACKUP_FOLDER.exists(): os.startfile(str(BACKUP_FOLDER))
        else: messagebox.showinfo("Hearth","No backups yet. Created automatically when you sync.")

    def _open_donate(self):
        import webbrowser; webbrowser.open(DONATE)

    def _open_support(self):
        import webbrowser
        webbrowser.open(f"mailto:{SUPPORT}?subject=Hearth%20Feedback&body=Version%3A%20{VERSION}%0A%0A")

    def _steam_cloud_help(self):
        messagebox.showinfo("Hearth — Steam Cloud",
            "Some games save to Steam Cloud by default. Hearth needs local save files.\n\n"
            "To disable Steam Cloud for a game:\n"
            "Steam → right-click game → Properties → General\n"
            "Uncheck 'Keep game save files in the Steam Cloud'\n\n"
            "Games that require this:\n• Core Keeper\n• Enshrouded")

    def _help_steam_id(self):
        messagebox.showinfo("Hearth — Finding Your Steam ID",
            "1. Open Steam\n"
            "2. Click your profile name at the top right\n"
            "3. Select 'View Profile'\n"
            "4. Look at the URL in your browser\n"
            "5. The long number at the end is your Steam ID\n\n"
            "Example: steamcommunity.com/profiles/76561198292066021\n\n"
            "Your Steam ID is: 76561198292066021\n\n"
            "Only needed for Icarus and Core Keeper.")

    def _help_shared_folder(self):
        messagebox.showinfo("Hearth — Setting Up Your Shared Folder",
            "1. Install Google Drive for Desktop\n"
            "   drive.google.com/drive/download\n\n"
            "2. Open Google Drive settings\n"
            "   Set sync mode to 'Mirror Files'\n\n"
            "3. Create a folder called HearthSync in your Drive\n\n"
            "4. Share that folder with everyone in your group\n"
            "   (Editor access required)\n\n"
            "5. In Hearth, browse to that folder\n\n"
            "⚠  Mirror Files mode is required.\n"
            "Stream Files will not work.")

    def _show_naming_rules(self):
        messagebox.showinfo("Hearth — World Naming Rules",
            "No two players in your group should have a world with the same name.\n\n"
            "Hearth identifies shared worlds by their filename.\n"
            "Duplicate names between players cause sync conflicts.\n\n"
            "Solution: Rename your world inside the game before sharing it.")

    def _check_conflict(self, game_key, world_id, local_file):
        """Compare local, own Drive, and all other players' Drive copies.
        If all match — silent. One clearly newer — auto pull. Genuine conflict — popup."""
        drive    = self.cfg.get("drive_folder","")
        username = self.cfg.get("username","")
        if not drive or not username or not local_file: return

        local_path = Path(str(local_file))
        local_h    = file_hash(str(local_path)) if local_path.exists() else None
        local_mtime= local_path.stat().st_mtime if local_path.exists() else 0

        # Gather all versions: local + every player's Drive copy
        versions = []
        if local_path.exists():
            versions.append({
                "label":    "Your PC",
                "hash":     local_h,
                "mtime":    local_mtime,
                "source":   "local",
                "path":     str(local_path),
            })

        statuses = read_all_statuses(drive, game_key, world_id)
        for s in statuses:
            wf   = Path(s["folder"])
            info = GAMES.get(game_key,{})
            ext  = info.get("save_ext","")
            drive_file = next((f for f in _drive_files(wf) if ext and f.name.endswith(ext)), None)
            if not drive_file: continue
            dh = file_hash(str(drive_file))
            dm = drive_file.stat().st_mtime if drive_file.exists() else 0
            owner_label = "Your Drive" if s["owner"]==username else f"{s['owner']}'s Drive"
            versions.append({
                "label":   owner_label,
                "hash":    dh,
                "mtime":   dm,
                "source":  "drive",
                "owner":   s["owner"],
                "entry":   {"world_id": world_id, "owner": s["owner"],
                            "display_name": world_id},
            })

        if len(versions) < 2: return

        hashes = [v["hash"] for v in versions if v["hash"]]
        if len(set(hashes)) <= 1: return  # All match — silent

        # Find newest by timestamp
        newest = max(versions, key=lambda v: v["mtime"])
        others = [v for v in versions if v["hash"] != newest["hash"]]

        # If only one differs and timestamps are clear — auto resolve
        timestamps = [v["mtime"] for v in versions]
        spread = max(timestamps) - min(timestamps)
        if spread > 120:  # More than 2 minutes apart — timestamps are trustworthy
            if newest["source"] == "drive" and newest["label"] != "Your Drive":
                # Someone else's Drive is newest — pull it
                entry = newest.get("entry",{})
                def do_pull(e=entry):
                    ok,_ = pull_world(drive, game_key, e["owner"], e, self.cfg, is_own=False)
                    if ok:
                        self._log(f"⬇ Auto-resolved: pulled newer version from {newest['label']}")
                        self.after(0, self._force_full_scan)
                threading.Thread(target=do_pull, daemon=True).start()
                return
            elif newest["source"] == "local":
                # Local is newest — push it
                worlds = get_local_worlds(game_key, self.cfg)
                we = next((w for w in worlds if w["name"]==world_id), None)
                if we:
                    def do_push(w=we):
                        push_world(drive, game_key, username, w, self.cfg)
                        self._log(f"⬆ Auto-resolved: pushed newer local version of {world_id}")
                    threading.Thread(target=do_push, daemon=True).start()
                return

        # Genuine conflict — show popup on main thread
        self.after(0, lambda: self._show_conflict_popup(game_key, world_id, versions))

    def _show_conflict_popup(self, game_key, world_id, versions):
        """Show conflict resolution popup — user picks which version to use."""
        drive    = self.cfg.get("drive_folder","")
        username = self.cfg.get("username","")
        win = ctk.CTkToplevel(self)
        win.title("Save Conflict Detected")
        win.geometry("460x420")
        win.configure(fg_color=C["bg"])
        win.grab_set(); win.resizable(False,False)
        ctk.CTkFrame(win,fg_color="#c0392b",height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,text="⚠  Save Conflict",font=ctk.CTkFont("Segoe UI",16,"bold"),
                     text_color=C["text"]).pack(pady=(14,4))
        ctk.CTkLabel(win,
            text=f"Multiple different versions of '{world_id}' were found.\nPick the one you want to keep — all others will be replaced.",
            font=ctk.CTkFont("Segoe UI",11),text_color=C["muted"],justify="center",
            wraplength=400).pack(pady=(0,10))

        sf = ctk.CTkScrollableFrame(win,fg_color=C["card"],corner_radius=8,height=220)
        sf.pack(fill="x",padx=20,pady=(0,10))

        selected = {"version": None}

        def pick(v):
            selected["version"] = v
            confirm_btn.configure(state="normal",
                text=f"Use version from {v['label']}")

        for v in versions:
            ts = datetime.fromtimestamp(v["mtime"]).strftime("%m/%d %I:%M %p") if v["mtime"] else "Unknown"
            row = ctk.CTkFrame(sf,fg_color=C["card2"],corner_radius=6)
            row.pack(fill="x",padx=8,pady=4)
            ctk.CTkLabel(row,text=v["label"],font=ctk.CTkFont("Segoe UI",12,"bold"),
                         text_color=C["accent"],anchor="w").pack(side="left",padx=12,pady=8)
            ctk.CTkLabel(row,text=f"Last modified: {ts}",
                         font=ctk.CTkFont("Segoe UI",10),text_color=C["muted"],
                         anchor="e").pack(side="left",fill="x",expand=True,padx=4)
            ctk.CTkButton(row,text="Use This",width=80,height=28,
                fg_color=C["accent"],hover_color=C["accent2"],
                font=ctk.CTkFont("Segoe UI",10),corner_radius=4,
                command=lambda vv=v: pick(vv)).pack(side="right",padx=8,pady=6)

        confirm_btn = ctk.CTkButton(win,text="Select a version above",height=40,
            fg_color=C["card"],hover_color=C["border"],text_color=C["muted"],
            font=ctk.CTkFont("Segoe UI",12,"bold"),corner_radius=8,state="disabled")
        confirm_btn.pack(fill="x",padx=20,pady=(0,6))

        def confirm():
            v = selected["version"]
            if not v: return
            win.destroy()
            def do_resolve():
                if v["source"] == "local":
                    worlds = get_local_worlds(game_key, self.cfg)
                    we = next((w for w in worlds if w["name"]==world_id), None)
                    if we: push_world(drive, game_key, username, we, self.cfg)
                    self._log(f"✅ Conflict resolved — kept local version of {world_id}")
                else:
                    entry = v.get("entry",{})
                    is_own = v.get("owner","") == username
                    pull_world(drive, game_key, entry["owner"], entry, self.cfg, is_own=is_own)
                    self._log(f"✅ Conflict resolved — pulled version from {v['label']}")
                self.after(0, self._force_full_scan)
            threading.Thread(target=do_resolve, daemon=True).start()

        confirm_btn.configure(command=confirm)
        ctk.CTkButton(win,text="Decide Later",height=32,
            fg_color="transparent",hover_color=C["border"],text_color=C["muted"],
            font=ctk.CTkFont("Segoe UI",11),corner_radius=8,
            command=win.destroy).pack(fill="x",padx=20,pady=(0,14))

    def _show_push_failed_popup(self, game_key, world_id):
        """Show non-blocking popup when push verification fails."""
        self._set_tray_icon("error")
        win = ctk.CTkToplevel(self)
        win.title("Sync Failed")
        win.geometry("400x200")
        win.configure(fg_color=C["bg"])
        win.resizable(False,False)
        ctk.CTkFrame(win,fg_color="#c0392b",height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,
            text=f"⚠  Sync Failed",
            font=ctk.CTkFont("Segoe UI",15,"bold"),text_color=C["text"]).pack(pady=(16,6))
        ctk.CTkLabel(win,
            text=f"Hearth couldn't verify that '{world_id}' reached Google Drive.\nYour friends may not have the latest version.",
            font=ctk.CTkFont("Segoe UI",11),text_color=C["muted"],
            justify="center",wraplength=360).pack(pady=(0,14))
        btn_row = ctk.CTkFrame(win,fg_color="transparent")
        btn_row.pack()
        def retry():
            win.destroy()
            self._set_tray_icon("nominal")
            worlds = get_local_worlds(game_key, self.cfg)
            we = next((w for w in worlds if w["name"]==world_id), None)
            if we:
                drive = self.cfg.get("drive_folder","")
                username = self.cfg.get("username","")
                def do_retry():
                    ok = push_world(drive, game_key, username, we, self.cfg)
                    if ok:
                        self._log(f"✅ Retry succeeded: {world_id}")
                    else:
                        self._log(f"⚠ Retry failed: {world_id} — check your Drive connection")
                        self.after(0, lambda: self._set_tray_icon("error"))
                threading.Thread(target=do_retry, daemon=True).start()
        ctk.CTkButton(btn_row,text="Try Again",
            fg_color=C["accent"],hover_color=C["accent2"],
            font=ctk.CTkFont("Segoe UI",12),command=retry).pack(side="left",padx=8)
        ctk.CTkButton(btn_row,text="Dismiss",
            fg_color=C["card"],hover_color=C["border"],text_color=C["muted"],
            font=ctk.CTkFont("Segoe UI",12),
            command=lambda:(win.destroy(),self._set_tray_icon("nominal"))).pack(side="left",padx=8)

    def _show_invite(self):
        """Show invite message with copy and email buttons."""
        drive = self.cfg.get("drive_folder","")
        username = self.cfg.get("username","") or "your friend"
        msg = (
            f"Hey! I'm using Hearth to share game worlds — it's free and takes about 5 minutes to set up.\n\n"
            f"Here's how to join:\n"
            f"1. Download Google Drive for Desktop from drive.google.com/drive/downloads\n"
            f"   — set it to Mirror Files mode (not Stream Files)\n"
            f"2. Download Hearth from github.com/{GITHUB_REPO}/releases\n"
            f"3. Open Hearth, enter your name, and set your Drive folder to the HearthSync folder I shared with you\n\n"
            f"I'll share the HearthSync folder with your Google email — send it to me and I'll get you set up."
        )
        win = ctk.CTkToplevel(self)
        win.title("Invite a Friend")
        win.geometry("500x380")
        win.configure(fg_color=C["bg"])
        win.grab_set(); win.resizable(False,False)
        ctk.CTkFrame(win,fg_color=C["accent"],height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,text="Invite a Friend",font=ctk.CTkFont("Segoe UI",16,"bold"),
                     text_color=C["text"]).pack(pady=(16,8))
        tb = ctk.CTkTextbox(win,fg_color=C["card"],text_color=C["text"],
                            font=ctk.CTkFont("Segoe UI",11),corner_radius=8,
                            border_width=0,wrap="word",height=220)
        tb.pack(fill="x",padx=20,pady=(0,10))
        tb.insert("1.0",msg); tb.configure(state="disabled")
        btn_row = ctk.CTkFrame(win,fg_color="transparent")
        btn_row.pack(pady=(0,16))
        def copy_msg():
            self.clipboard_clear(); self.clipboard_append(msg)
            copy_btn.configure(text="✓ Copied!")
            win.after(2000, lambda: copy_btn.configure(text="Copy Message"))
        copy_btn = ctk.CTkButton(btn_row,text="Copy Message",
            fg_color=C["accent"],hover_color=C["accent2"],
            font=ctk.CTkFont("Segoe UI",12),command=copy_msg)
        copy_btn.pack(side="left",padx=8)
        def send_email():
            import urllib.parse
            subject = urllib.parse.quote("Join me on Hearth")
            body = urllib.parse.quote(msg)
            subprocess.Popen(f'start "" "mailto:?subject={subject}&body={body}"',shell=True)
        ctk.CTkButton(btn_row,text="Send via Email",
            fg_color=C["card"],hover_color=C["border"],text_color=C["muted"],
            font=ctk.CTkFont("Segoe UI",12),command=send_email).pack(side="left",padx=8)
        ctk.CTkButton(btn_row,text="Close",
            fg_color=C["card"],hover_color=C["border"],text_color=C["muted"],
            font=ctk.CTkFont("Segoe UI",12),command=win.destroy).pack(side="left",padx=8)

    def _show_status(self):
        """Show current Hearth status — drive, last sync, active locks."""
        drive = self.cfg.get("drive_folder","")
        username = self.cfg.get("username","") or "Not set"
        drive_ok = Path(drive).exists() if drive else False
        shared_count = sum(1 for g in self.shared_worlds.values() for v in g.values() if v)
        # Find any active locks
        locks = []
        if drive and drive_ok:
            for gk in GAMES:
                for entry in get_all_shared_worlds(drive,gk):
                    if entry.get("lock"):
                        who = entry["lock"].get("user","?")
                        locks.append(f"{who} is hosting {entry['display_name']} ({gk})")
        win = ctk.CTkToplevel(self)
        win.title("Hearth Status")
        win.geometry("420x320")
        win.configure(fg_color=C["bg"])
        win.grab_set(); win.resizable(False,False)
        ctk.CTkFrame(win,fg_color=C["accent"],height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,text="Status",font=ctk.CTkFont("Segoe UI",16,"bold"),
                     text_color=C["text"]).pack(pady=(16,8))
        card = ctk.CTkFrame(win,fg_color=C["card"],corner_radius=10)
        card.pack(fill="x",padx=20,pady=(0,12))
        def row(label, value, color=None):
            f = ctk.CTkFrame(card,fg_color="transparent")
            f.pack(fill="x",padx=16,pady=4)
            ctk.CTkLabel(f,text=label,font=ctk.CTkFont("Segoe UI",11),
                         text_color=C["muted"],width=140,anchor="w").pack(side="left")
            ctk.CTkLabel(f,text=value,font=ctk.CTkFont("Segoe UI",11,"bold"),
                         text_color=color or C["text"],anchor="w").pack(side="left")
        ctk.CTkFrame(card,fg_color="transparent",height=6).pack()
        row("Your name", username)
        row("Drive folder", "Connected ✓" if drive_ok else "Not found ✗",
            C["green"] if drive_ok else C["red"] if hasattr(C,"red") else "#e05555")
        row("Worlds shared", str(shared_count))
        row("Currently hosting", locks[0] if locks else "Nobody")
        if len(locks) > 1:
            for l in locks[1:]: row("", l)
        row("Hearth version", f"v{VERSION}")
        ctk.CTkFrame(card,fg_color="transparent",height=6).pack()
        ctk.CTkButton(win,text="Close",fg_color=C["accent"],hover_color=C["accent2"],
            font=ctk.CTkFont("Segoe UI",12),command=win.destroy).pack(pady=(0,16))

    def _show_changelog(self):
        """Show version history."""
        log = (
            "v1.6  —  Current\n"
            "  • Drive folder reachability check on startup and every 30 min\n"
            "  • Persistent warning banner when Google Drive folder is unreachable\n"
            "  • Others' worlds show 'Available' not 'Downloaded' if not opted in\n"
            "  • Stale lock scan runs every 10 min — self-owned locks only\n"
            "  • Fixed bug where stale lock cleanup could clear other users' locks\n"
            "  • Post-game push waits for save file to stop changing\n"
            "  • Fixed mid-session backup firing immediately on game launch\n"
            "  • Per-world participation toggle for others' shared worlds — default OFF\n"
            "  • World name validation at share time\n"
            "  • World names sanitized when building Drive paths\n"
            "  • hearth_status and internal files filtered from world list\n"
            "  • Valheim shows clear message when save folder is missing\n\n"
            "v1.5\n"
            "  • Smart conflict detection — hash + timestamp comparison\n"
            "  • Conflict resolution UI — choose Drive or local version\n"
            "  • Push failed popup with retry option\n"
            "  • Mid-session backup every 25 minutes\n\n"
            "v1.3\n"
            "  • Valheim world detection fixed for all users\n"
            "  • Game sections now collapsible\n"
            "  • Update check on startup\n"
            "  • Invite a Friend button\n\n"
            "v1.1\n"
            "  • Valheim added (initial support)\n"
            "  • 7 new games added (unverified)\n\n"
            "v1.0\n"
            "  • Initial public release\n"
            "  • Icarus, Terraria, Core Keeper, Enshrouded, Sons of the Forest\n"
        )
        win = ctk.CTkToplevel(self)
        win.title("Hearth — Changelog")
        win.geometry("440x380")
        win.configure(fg_color=C["bg"])
        win.grab_set(); win.resizable(False,False)
        ctk.CTkFrame(win,fg_color=C["accent"],height=3,corner_radius=0).pack(fill="x")
        ctk.CTkLabel(win,text="Changelog",font=ctk.CTkFont("Segoe UI",16,"bold"),
                     text_color=C["text"]).pack(pady=(16,8))
        tb = ctk.CTkTextbox(win,fg_color=C["card"],text_color=C["text"],
                            font=ctk.CTkFont("Consolas",11),corner_radius=8,
                            border_width=0,height=260)
        tb.pack(fill="x",padx=20,pady=(0,10))
        tb.insert("1.0",log); tb.configure(state="disabled")
        ctk.CTkButton(win,text="Close",fg_color=C["accent"],hover_color=C["accent2"],
            font=ctk.CTkFont("Segoe UI",12),command=win.destroy).pack(pady=(0,16))

    def _show_about(self):
        messagebox.showinfo("Hearth",
            f"Hearth v{VERSION}\n\n"
            "Share game worlds with your crew.\n"
            "No dedicated server required.\n\n"
            f"{COPYRIGHT}\n\n"
            f"Support: {SUPPORT}\n"
            f"Donate: {DONATE}")

    # ── Monitor ───────────────────────────────────────────────────────────────
    def _start_monitor(self):
        self.monitor_running=True
        self.monitor_thread=threading.Thread(target=self._monitor_loop,daemon=True)
        self.monitor_thread.start(); self._log("👁  Background monitor active.")

    def _monitor_loop(self):
        username=self.cfg.get("username",""); last_backup={}
        while self.monitor_running:
            drive=self.cfg.get("drive_folder",""); active=any_game_running()
            if active and self.game_was_running is None:
                self.game_was_running=active; self._log(f"🎮 {active} detected.")
                # Seed last_backup now so the first interval check doesn't fire immediately
                now=time.time()
                for wid,shared in self.shared_worlds.get(active,{}).items():
                    if shared: last_backup[wid]=now
                # Pre-launch sync — hash+timestamp, never blindly pull over newer local
                if drive:
                    for gk2 in GAMES:
                        for entry in get_all_shared_worlds(drive,gk2):
                            if entry["lock"] or entry["owner"]==username: continue
                            # Skip worlds user hasn't opted into
                            if not self.participated_worlds.get(gk2,{}).get(entry["world_id"],False): continue
                            try:
                                result=compare_local_and_drive(drive,gk2,entry["owner"],
                                                               entry["world_id"],self.cfg)
                                name=entry["display_name"]
                                if result=="drive_newer" or result=="drive_only":
                                    self.after(0,lambda: self._set_tray_icon("syncing"))
                                    ok,_=pull_world(drive,gk2,entry["owner"],entry,self.cfg,is_own=False)
                                    if ok: self._log(f"⬇ Pre-launch pulled: {name} — Drive was newer")
                                    else:  self._log(f"⚠ Pre-launch pull failed: {name}")
                                    self.after(0,lambda: self._set_tray_icon("nominal"))
                                elif result=="same":
                                    self._log(f"✓ Pre-launch check: {name} — already in sync")
                                elif result in ("local_newer","local_only"):
                                    self._log(f"✓ Pre-launch check: {name} — local is newer, keeping local")
                                elif result=="conflict":
                                    self._log(f"⚠ Pre-launch conflict: {name} — files differ, keeping local to protect active session")
                            except Exception: pass
                    # Own shared worlds — push if local newer, pull if Drive newer
                    for wid,shared in self.shared_worlds.get(active,{}).items():
                        if not shared: continue
                        try:
                            result=compare_local_and_drive(drive,active,username,wid,self.cfg)
                            if result=="drive_newer":
                                worlds=get_local_worlds(active,self.cfg)
                                we=next((w for w in worlds if w["name"]==wid),{"name":wid,"file":None})
                                ok,_=pull_world(drive,active,username,we,self.cfg,is_own=True)
                                if ok: self._log(f"⬇ Pre-launch updated own world: {wid} — Drive was newer")
                                else:  self._log(f"⚠ Pre-launch pull failed for own world: {wid}")
                            elif result=="local_newer":
                                self._log(f"✓ Pre-launch check: {wid} — local is newer, no pull needed")
                            elif result=="same":
                                self._log(f"✓ Pre-launch check: {wid} — in sync")
                            elif result=="conflict":
                                self._log(f"⚠ Pre-launch conflict on own world: {wid} — keeping local")
                        except Exception: pass
                # Now push current state and lock
                for wid,shared in self.shared_worlds.get(active,{}).items():
                    if shared and drive:
                        worlds=get_local_worlds(active,self.cfg)
                        we=next((w for w in worlds if w["name"]==wid),{"name":wid,"file":None})
                        push_world(drive,active,username,we,self.cfg)
                        wf=get_drive_world_folder(drive,active,username,wid)
                        _write_lock(wf,username); self._log(f"🔒 Locked: {wid}")
            elif not active and self.game_was_running is not None:
                closed=self.game_was_running; self.game_was_running=None
                self._log(f"{closed} closed — waiting for save to finish writing...")
                for wid,shared in self.shared_worlds.get(closed,{}).items():
                    if not shared or not drive: continue
                    worlds=get_local_worlds(closed,self.cfg)
                    we=next((w for w in worlds if w["name"]==wid),{"name":wid,"file":None})
                    local=we.get("file")
                    # File-watch loop — wait until save file stops changing, max 60s
                    if local and Path(str(local)).exists():
                        lp=Path(str(local)); prev_mtime=lp.stat().st_mtime; stable=0
                        for _ in range(30):  # 30 x 2s = 60s max
                            time.sleep(2)
                            try:
                                cur_mtime=lp.stat().st_mtime
                                if cur_mtime==prev_mtime:
                                    stable+=1
                                    if stable>=2: break  # stable for 4s — safe to push
                                else:
                                    prev_mtime=cur_mtime; stable=0
                            except: break
                        backup_local(local,closed,username,wid); self._log(f"📦 Backed up: {wid}")
                    ok=push_world(drive,closed,username,we,self.cfg)
                    wf=get_drive_world_folder(drive,closed,username,wid)
                    _clear_lock(wf,username)
                    if ok:
                        self._log(f"✅ Synced and unlocked: {wid}")
                        self.after(0,lambda w=wid,g=closed:self._toast(f"Hearth — {g}",f"'{w}' synced to Drive ✓"))
                        lf=we.get("file")
                        self.after(8000,lambda g=closed,w=wid,f=lf:self._check_conflict(g,w,f))
                    else:
                        self._log(f"⚠ Push may have failed: {wid} — check Drive connection")
                        self.after(0,lambda g=closed,w=wid:self._show_push_failed_popup(g,w))
            elif active and self.game_was_running is not None:
                now=time.time()
                for wid,shared in self.shared_worlds.get(active,{}).items():
                    if not shared: continue
                    if now-last_backup.get(wid,now)>=1500:
                        worlds=get_local_worlds(active,self.cfg)
                        we=next((w for w in worlds if w["name"]==wid),None)
                        if we and we.get("file") and Path(str(we["file"])).exists():
                            backup_local(we["file"],active,username,wid)
                            self._log(f"📦 Mid-session backup: {wid}"); last_backup[wid]=now
            elif not active and self.game_was_running is None:
                if drive and not self._syncing:
                    for gk in GAMES:
                        for entry in get_all_shared_worlds(drive,gk):
                            if entry["lock"] or entry["owner"]==username: continue
                            # Skip worlds user hasn't opted into
                            if not self.participated_worlds.get(gk,{}).get(entry["world_id"],False): continue
                            try:
                                result=compare_local_and_drive(drive,gk,entry["owner"],
                                                               entry["world_id"],self.cfg)
                                if result=="drive_newer" or result=="drive_only":
                                    self.after(0,lambda: self._set_tray_icon("syncing"))
                                    ok,_=pull_world(drive,gk,entry["owner"],entry,self.cfg,is_own=False)
                                    if ok: self._log(f"⬇ Auto-pulled: {entry['display_name']} — Drive was newer")
                                    self.after(0,lambda: self._set_tray_icon("nominal"))
                            except Exception:
                                self.after(0,lambda: self._set_tray_icon("nominal"))
            time.sleep(10)

    # ── Logging ───────────────────────────────────────────────────────────────
    def _toast(self, title, message):
        """Show a Windows balloon/toast notification using ctypes — no extra install needed."""
        try:
            import ctypes
            # Use balloon tip via Shell_NotifyIcon is complex — use simpler MessageBeep + tray
            # Fallback: just log it. Real toast requires win32api or winotify.
            # Use PowerShell toast — works on Windows 10+ without any pip install
            import subprocess
            ps = (
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
                f"$t=[Windows.UI.Notifications.ToastTemplateType]::ToastText02;"
                f"$xml=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($t);"
                f"$xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{title}')) | Out-Null;"
                f"$xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{message}')) | Out-Null;"
                f"$toast=[Windows.UI.Notifications.ToastNotification]::new($xml);"
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Hearth').Show($toast);"
            )
            subprocess.Popen(["powershell","-WindowStyle","Hidden","-Command",ps],
                             creationflags=0x08000000)
        except Exception:
            pass  # toast is best-effort, never crash for it

    def _log(self,msg):
        def _do():
            self.log_box.configure(state="normal")
            self.log_box.insert("end",f"[{ts()}] {msg}\n")
            self.log_box.see("end"); self.log_box.configure(state="disabled")
        self.after(0,_do)
        try:
            drive=self.cfg.get("drive_folder","")
            if drive:
                lp=Path(drive)/LOG_FILENAME
                with open(lp,"a") as f: f.write(f"[{ts_full()}] {msg}\n")
        except: pass

    # ── Close ─────────────────────────────────────────────────────────────────
    def _minimize_or_close(self):
        """Close window but keep running in tray if available."""
        if HAVE_TRAY and self.tray_icon:
            self._hide_window()
        else:
            self._on_close()

    def _on_close(self):
        self.monitor_running=False
        if self.tray_icon:
            try: self.tray_icon.stop()
            except: pass
        self.destroy()


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__=="__main__":
    import socket
    # Use a socket-based single instance lock — more reliable than PID files
    _lock_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        _lock_socket.bind(("127.0.0.1",47832))  # Hearth's reserved port
    except OSError:
        # Already running — bring existing window to front if possible
        sys.exit(0)
    try:
        app=Hearth(); app.mainloop()
    finally:
        _lock_socket.close()
