# Hearth v1.0
# Copyright 2026 Hearth Software. All rights reserved.
# Unauthorized copying, distribution, or modification is prohibited.
# Built by Chester Houston. hearthforpc@gmail.com

# =============================================================================
# PROJECT LOG — updated each build. Read this to get full context on the
# architecture, known issues, business roadmap, and session history.
# =============================================================================
#
# # HearthSync Project Log
# Last updated: 2026-04-17
# 
# 
# 
# ## Business Context & Roadmap
# 
# ### Current model
# - Free download, donation button only (https://buymeacoffee.com/hearthapp)
# - No license server, no accounts, no subscription
# 
# 
# 
# 
# 
# 
# 
# ### Why Icarus first
# - Cooperative-focused playerbase
# - Save system is straightforward (no slot remapping complexity)
# - Icarus push/pull was rock solid before today's session
# - Community channels: r/Icarus on Reddit, Discord, YouTube mid-size content creators
# 
# ### Broader use case (future consideration)
# The core engine — file locking + sync coordination for files only one person edits at a time — applies beyond games. Examples: QuickBooks company files, CAD drawings, Adobe Premiere projects, shared Excel trackers that break with simultaneous edits. Business market is a harder sell (needs enterprise-looking UI, support, liability) but the technology transfers directly with a reskin.
# 
# ### Key development principle
# Icarus is the launch target. Every change should be evaluated against "does this keep Icarus solid." Enshrouded complexity should never break the Icarus path.
# 
# ---
# 
# ## Project Overview
# **App name:** HearthSync (branded as "Hearth")  
# **Version in progress:** 0.9.4  
# **Purpose:** Share game world save files between players via Google Drive as a shared folder. No dedicated server required.  
# **Language:** Python, using customtkinter for UI  
# **Entry point:** `hearth_sync.pyw` (run via `HearthSync.bat`)  
# **Config file:** `~/.hearth_config.json`  
# **Author:** Chester Houston — hearthforpc@gmail.com  
# **Donate:** https://buymeacoffee.com/hearthapp
# 
# ---
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
# ---
# 
# ## Bugs Fixed in 0.9.4
# 
# ### None folder in Drive
# - **Cause:** Monitor loop used fallback dict `{"name": wid, "file": None}` when world not found. `get_drive_world_folder` created the folder before `_push_standard` could check if file existed.
# - **Fix:** `_push_standard` now validates world_id and file exist before ever calling `get_drive_world_folder`
# 
# ### Own files being copied into others' folders
# - **Cause:** `_pull_standard` copied everything in the Drive folder indiscriminately
# - **Fix:** Now filters by `save_ext` — only pulls files matching the game's expected extension
# 
# ### Enshrouded world not showing in game after pull
# - **Cause 1:** `{hex_id}-1` was missing from `get_enshrouded_files` pattern list — not pushed or pulled
# - **Fix:** Added `f"{hex_id}-1"` to patterns
# - **Cause 2:** Index files had `"latest": N` pointing to a numbered backup that didn't exist in the new slot
# - **Fix:** After pull, both `{local_hex}-index` and `{local_hex}_info-index` are patched to `"latest": 0`
# 
# ### Steam Cloud warning missing
# - **Cause:** Game section was skipped entirely when no local saves AND no shared worlds found
# - **Fix:** Steam Cloud games now always show in the worlds list with actionable warning text and fix instructions when no local save folder detected. Others' shared worlds still show even when local saves are missing.
# 
# ### Enshrouded push not worldmap-aware
# - **Cause:** Push always used the local hex as the Drive folder name, so Player B's push of Player A's world went to the wrong folder
# - **Fix:** `_push_enshrouded` now scans Drive worldmaps to find the correct remote folder before pushing
# 
# ---
# 
# 
# 
# =============================================================================

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import json, os, shutil, time, threading, subprocess, sys, hashlib
from pathlib import Path
from datetime import datetime

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

VERSION   = "1.0"
COPYRIGHT = "Copyright 2026 Hearth Software. All rights reserved."
SUPPORT   = "hearthforpc@gmail.com"
DONATE    = "https://buymeacoffee.com/hearthapp"

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_FILE   = Path.home() / ".hearth_config.json"
LOCK_FILENAME = "hearth.lock"
META_FILENAME = "meta.json"
MAP_FILENAME  = "worldmap.json"
LOG_FILENAME  = "hearth.log"
BACKUP_FOLDER = Path.home() / "Hearth_Backups"
ICON_PATH        = Path(__file__).parent / "hearth_flame_cropped.png"
ICO_PATH         = Path(__file__).parent / "hearth.ico"
TRAY_ORANGE_PATH = Path(__file__).parent / "tray_orange.png"  # nominal
TRAY_BLUE_PATH   = Path(__file__).parent / "tray_blue.png"    # update available
TRAY_GREEN_PATH  = Path(__file__).parent / "tray_green.png"   # syncing
TRAY_RED_PATH    = Path(__file__).parent / "tray_red.png"     # error

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
            Path("C:/Program Files (x86)/Steam/userdata")/_steam_id32(cfg.get("steam_id",""))/str(892970)/"remote"/"worlds",
        ],
        "save_ext":".db","backup_pattern":".old","needs_steam_id":False,
        "launch_cmd":"steam://rungameid/892970","steam_cloud":False,
        "slot_based":False,"paired_ext":".fwl",
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
            pp=Path(str(p)).resolve()
            if pp.exists(): return pp
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
    results=[]
    for f in folder.iterdir():
        if f.is_file() and ext and f.name.endswith(ext) and backup not in f.name and ".mine" not in f.name:
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
def get_drive_world_folder(drive,game_key,owner,world_id):
    p=Path(drive)/game_key/owner/str(world_id); p.mkdir(parents=True,exist_ok=True); return p

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

def backup_local(local_file, game_key, owner, world_id):
    """Back up a single file before overwriting. Always runs — no exceptions."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest  = BACKUP_FOLDER / game_key / owner / str(world_id) / stamp
    dest.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(local_file, dest / Path(local_file).name)
        return True
    except Exception:
        return False

def backup_slot(folder, hex_id, game_key, owner, world_id):
    """Back up ALL files for an Enshrouded hex slot before overwriting."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest  = BACKUP_FOLDER / game_key / owner / str(world_id) / stamp
    dest.mkdir(parents=True, exist_ok=True)
    backed = 0
    for f in folder.iterdir():
        if f.is_file() and f.name.startswith(hex_id):
            try:
                shutil.copy2(f, dest / f.name)
                backed += 1
            except Exception:
                pass
    return backed

def get_all_shared_worlds(drive,game_key):
    base=Path(drive)/game_key
    if not base.exists(): return []
    results=[]
    for od in base.iterdir():
        if not od.is_dir(): continue
        for wd in od.iterdir():
            if not wd.is_dir(): continue
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
    return True

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
        if f.name in (LOCK_FILENAME, META_FILENAME, MAP_FILENAME, LOG_FILENAME):
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
        if f.name in (LOCK_FILENAME, META_FILENAME, MAP_FILENAME, LOG_FILENAME):
            continue
        # Only copy files matching this game's save extension or paired extension
        if ext and not f.name.endswith(ext) and not (paired_ext and f.name.endswith(paired_ext)):
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
    try:
        return [f for f in Path(wf).iterdir()
                if f.is_file() and f.name not in
                (LOCK_FILENAME, META_FILENAME, MAP_FILENAME, LOG_FILENAME)]
    except Exception:
        return []

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

    # ── System tray ───────────────────────────────────────────────────────────
    def _load_tray_img(self, path):
        """Load a tray icon image, fall back to default if missing."""
        try:
            if Path(path).exists():
                return PILImage.open(str(path)).convert("RGBA").resize((64,64))
        except Exception:
            pass
        # Fallback to original icon
        if ICON_PATH.exists():
            return PILImage.open(str(ICON_PATH)).convert("RGBA").resize((64,64))
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
                     ("---",None),("Refresh",self._scan_all_worlds)])

    def _menu_game(self):
        self._popup([("Set Custom Save Path",self._browse_save_manual),
                     ("Steam Cloud Help",self._steam_cloud_help)])

    def _menu_help(self):
        self._popup([("How to Find Your Steam ID",self._help_steam_id),
                     ("How to Set Up Shared Folder",self._help_shared_folder),
                     ("World Naming Rules",self._show_naming_rules),
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
        self._clear_stale_locks()
        self._scan_all_worlds()
        self._auto_sync_on_startup()
        self._start_monitor()
        self._start_tray()

    def _clear_stale_locks(self):
        drive=self.cfg.get("drive_folder",""); username=self.cfg.get("username","")
        if not drive or not username: return
        for gk in GAMES:
            for entry in get_all_shared_worlds(drive,gk):
                lock=entry["lock"]
                if not lock: continue
                age=_lock_age_hours(lock)
                if lock.get("user")==username and not is_game_running(gk):
                    _clear_lock(entry["folder"],username); self._log(f"🧹 Cleared stale lock: {entry['display_name']}")
                elif age>8:
                    _clear_lock(entry["folder"]); self._log(f"🧹 Auto-cleared old lock ({age:.0f}h): {entry['display_name']}")

    def _auto_sync_on_startup(self):
        drive=self.cfg.get("drive_folder",""); username=self.cfg.get("username","")
        if not drive or not username: return
        for gk in GAMES:
            for entry in get_all_shared_worlds(drive,gk):
                # Only pull others' worlds on startup, never own
                if entry["owner"]==username: continue
                lock=entry["lock"]
                if lock: continue  # Don't pull locked worlds
                try:
                    if is_drive_newer(drive,gk,entry["owner"],entry["world_id"],self.cfg):
                        ok,_=pull_world(drive,gk,entry["owner"],entry,self.cfg,is_own=False)
                        if ok:
                            self._log(f"⬇ Auto-pulled: {entry['display_name']}")
                except Exception as e:
                    self._log(f"⚠ Skipped {entry['display_name']}: {e}")

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
        self.log_box=ctk.CTkTextbox(lf,height=130,fg_color=C["bg"],text_color="#8899aa",
                                     font=ctk.CTkFont("Consolas",11),corner_radius=6,
                                     border_width=0,state="disabled")
        self.log_box.pack(fill="x",padx=12,pady=(0,12))

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
        save_config(self.cfg); self._log("Configuration saved.")
        self._scan_all_worlds(); messagebox.showinfo("Hearth","Configuration saved!")

    # ── World scanning — stable widget approach (no flash) ───────────────────
    def _collect_world_data(self):
        """Collect all world data without touching UI. Returns structured list."""
        drive=self.cfg.get("drive_folder","")
        username=self.username_var.get() or self.cfg.get("username","")
        rows=[]
        for gk in list(GAMES.keys()):
            if gk=="Custom Game": continue
            my=get_local_worlds(gk,self.cfg)
            all_shared=get_all_shared_worlds(drive,gk) if drive and Path(drive).exists() else []
            others={}
            for e in all_shared:
                if e["owner"]!=username: others.setdefault(e["owner"],[]).append(e)
            info=GAMES.get(gk,{})
            # For Steam Cloud games with no local saves, always show the warning
            # even if there are no shared worlds either
            steam_cloud_problem = info.get("steam_cloud") and not my and not find_save_folder(gk,self.cfg)
            if not my and not others and not steam_cloud_problem: continue
            rows.append({"type":"game_header","game":gk})
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

    def _full_rebuild(self,rows,username,drive):
        """Full widget rebuild — only called when world list structure changes."""
        # Clear existing widgets and widget dict
        for w in self.world_frame.winfo_children(): w.destroy()
        self._world_widgets={}
        for row in rows:
            t=row["type"]
            if t=="game_header":
                gk=row["game"]
                sh=ctk.CTkFrame(self.world_frame,fg_color=C["card2"],corner_radius=8)
                sh.pack(fill="x",pady=(6,2))
                ctk.CTkLabel(sh,text=gk,font=ctk.CTkFont("Segoe UI",11,"bold"),
                             text_color=C["accent"]).pack(side="left",padx=10,pady=6)
                if GAMES.get(gk,{}).get("verified")==False:
                    ctk.CTkLabel(sh,text="unverified",font=ctk.CTkFont("Segoe UI",10),
                                 text_color=C["muted"]).pack(side="right",padx=(0,10))
                ctk.CTkButton(sh,text="Config",width=60,height=22,
                    font=ctk.CTkFont("Segoe UI",10),
                    fg_color=C["card"],hover_color=C["border"],text_color=C["muted"],
                    corner_radius=4,
                    command=lambda g=gk: self._config_game_path(g)).pack(side="right",padx=(0,8),pady=4)
            elif t=="section":
                ctk.CTkLabel(self.world_frame,text=f"  {row['text']}",
                    font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=C["muted"]).pack(anchor="w",padx=8,pady=(4,0))
            elif t=="cloud_warning":
                ctk.CTkLabel(self.world_frame,text=f"  ⚠  {row['msg']}",
                    font=ctk.CTkFont("Segoe UI",10),text_color=C["amber"],wraplength=500).pack(anchor="w",padx=8,pady=4)
            elif t=="empty":
                ctk.CTkLabel(self.world_frame,text="No save files found. Launch a supported game first.",
                    font=ctk.CTkFont("Segoe UI",11),text_color=C["muted"]).pack(pady=8,padx=8)
            elif t=="world":
                key=row["key"]
                r=ctk.CTkFrame(self.world_frame,fg_color=C["surface"],corner_radius=8)
                r.pack(fill="x",pady=2,padx=4)
                if row["is_mine"]:
                    var=ctk.BooleanVar(value=row["shared"])
                    we=row.get("world_entry")
                    ctk.CTkCheckBox(r,variable=var,text="",width=20,height=20,
                        fg_color=C["accent"],hover_color=C["accent2"],
                        border_color=C["border"],checkmark_color="white",
                        command=lambda n=row["world_id"],v=var,g=row["game"],x=we:
                            self._toggle_share(g,n,v,x)).pack(side="left",padx=(10,4),pady=10)
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
                # Store refs for in-place update
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
                        self._log(f"⚠ Download failed ({display}): {reason}")
                self.after(0, done)
            except Exception as e:
                self.after(0, lambda: self._pulling.discard(key))
                self.after(0, lambda: self._log(f"⚠ Download error ({display}): {e}"))
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
        if var.get() and drive and username and world_entry:
            push_world(drive,gk,username,world_entry,self.cfg,display_name)
            self._log(f"⬆ Shared and pushed: {display_name}")
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
                                ok,_=pull_world(drive,gk,entry["owner"],entry,self.cfg,is_own=False)
                                if ok:
                                    self._log(f"⬇ Synced: {entry['display_name']}"); pulled+=1
                        except Exception as e:
                            self._log(f"⚠ Skipped {entry['display_name']}: {e}")
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
                for wid,shared in self.shared_worlds.get(active,{}).items():
                    if shared and drive:
                        worlds=get_local_worlds(active,self.cfg)
                        we=next((w for w in worlds if w["name"]==wid),{"name":wid,"file":None})
                        push_world(drive,active,username,we,self.cfg)
                        wf=get_drive_world_folder(drive,active,username,wid)
                        _write_lock(wf,username); self._log(f"🔒 Locked: {wid}")
            elif not active and self.game_was_running is not None:
                closed=self.game_was_running; time.sleep(20)
                self.game_was_running=None; self._log(f"{closed} closed — syncing...")
                for wid,shared in self.shared_worlds.get(closed,{}).items():
                    if shared and drive:
                        worlds=get_local_worlds(closed,self.cfg)
                        we=next((w for w in worlds if w["name"]==wid),{"name":wid,"file":None})
                        local=we.get("file")
                        if local and Path(str(local)).exists():
                            backup_local(local,closed,username,wid); self._log(f"📦 Backed up: {wid}")
                        push_world(drive,closed,username,we,self.cfg)
                        wf=get_drive_world_folder(drive,closed,username,wid)
                        _clear_lock(wf,username); self._log(f"✅ Synced and unlocked: {wid}")
            elif active and self.game_was_running is not None:
                now=time.time()
                for wid,shared in self.shared_worlds.get(active,{}).items():
                    if not shared: continue
                    if now-last_backup.get(wid,0)>=1500:
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
                            try:
                                # Hash check — if content identical, do nothing silently
                                if not is_drive_newer(drive,gk,entry["owner"],entry["world_id"],self.cfg):
                                    continue
                                self.after(0,lambda: self._set_tray_icon("syncing"))
                                ok,_=pull_world(drive,gk,entry["owner"],entry,self.cfg,is_own=False)
                                if ok:
                                    self._log(f"⬇ Auto-pulled: {entry['display_name']}")
                                self.after(0,lambda: self._set_tray_icon("nominal"))
                            except Exception:
                                self.after(0,lambda: self._set_tray_icon("nominal"))
                                pass  # Silent — don't spam log with transient errors
            time.sleep(10)

    # ── Logging ───────────────────────────────────────────────────────────────
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
