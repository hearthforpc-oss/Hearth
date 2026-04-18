# Hearth v1.0
**Share game worlds with your crew. No dedicated server needed.**

Hearth syncs your game save files through Google Drive so you and your friends can play the same world — even when you're on different schedules.

Free. Open source. Your saves stay in your own Google Drive.

---

## Is Hearth safe?

**Yes. Here's exactly how it works:**

Hearth uses Google Drive folder sharing — the same technology you'd use to share a document with a coworker or family member. When you set up Hearth, you create one folder called HearthSync and share it with your gaming partners.

- Your partner only has access to that one folder. Not your email, not your other Drive files, not your Google account.
- Hearth never asks for your Google password or account credentials. It reads and writes to a folder you control through Google's own sync app.
- Your save files never touch anyone else's servers. They live in your Google Drive.
- Hearth is open source — every line of code is public on this page. Anyone can read exactly what it does.

**Who is Hearth designed for?**
People you already play games with — friends, family, your cousin. It is not designed for sharing with strangers. If you wouldn't share a Google Doc with someone, don't share your HearthSync folder with them either.

---

## Supported Games
- Icarus
- Valheim
- Terraria
- Terraria (tModLoader)
- Core Keeper
- Enshrouded ⚠ Steam Cloud must be disabled
- Sons of the Forest

---

## Requirements
- Windows PC
- [Google Drive for Desktop](https://drive.google.com/drive/downloads) — must use **Mirror Files** mode
- That's it. No Python required when using the exe.

---

## First Time Setup (everyone does this once)

### 1. Install Google Drive for Desktop
- Download and install from [drive.google.com/drive/downloads](https://drive.google.com/drive/downloads)
- Sign in with your Google account
- Open Google Drive settings → set sync mode to **Mirror Files** (not Stream Files)

### 2. Create a shared folder
- One person creates a folder called `HearthSync` in their Google Drive
- Right-click it → Share → add everyone's Google email with **Editor** access
- Everyone accepts the share — you now all sync the same folder

### 3. Run Hearth
- Download `Hearth.exe` from the [Releases page](https://github.com/hearthforpc-oss/Hearth/releases)
- Double-click it to launch — no installation needed
- Enter your name, Steam ID (Icarus / Core Keeper only), and browse to your HearthSync folder
- Click Save

### 4. Share a world
- Find your world in the list under your game
- Check the checkbox next to it — Hearth pushes it to Drive
- Your partner opens Hearth and hits **Sync Now** — the world appears under your name

---

## For developers (running from source)
If you want to run the Python script directly instead of the exe:

**Requirements:** Python 3.10+ — [python.org/downloads](https://python.org/downloads) (check "Add Python to PATH")

```
pip install customtkinter psutil pystray pillow pywin32
```

Then run `HearthSync.bat` or `hearth_sync.pyw` directly.

---

## Daily Use

**Playing solo while your partner is offline:**
1. Hit Sync Now — Hearth pulls the latest save
2. Launch your game and play
3. Close the game — Hearth auto-syncs when it detects the game closed

**Playing together:**
- One person hosts in-game, others join as normal
- Hearth handles the save when the host closes the game

---

## Tray Icon States
| Color | Meaning |
|-------|---------|
| 🟠 Orange | Hearth is running, idle |
| 🟢 Green | Currently syncing |
| 🔵 Blue | Update available |
| 🔴 Red | Issue detected |

Click the tray icon to restore the Hearth window.

---

## Enshrouded Notes
Enshrouded uses Steam Cloud by default. Hearth cannot see Steam Cloud saves.

**Disable Steam Cloud for Enshrouded:**
Steam → right-click Enshrouded → Properties → General → uncheck Steam Cloud

Both you and your partner must do this.

---

## Backups
Hearth creates automatic backups before every sync.
Location: `C:\Users\[You]\Hearth_Backups\`

---

## Troubleshooting

**World not showing in Hearth**
- Launch the game once so it creates its save folders
- For Enshrouded and Core Keeper: make sure Steam Cloud is disabled

**Save path wrong for my setup**
- Click the **Config** button next to the game name
- Browse to your actual save folder

**Lock is stuck**
- Go to Help → Unlock All in Hearth
- Or delete `hearth.lock` from the shared Drive folder manually

**Drive not synced yet**
- Wait 30–60 seconds after a session before your partner syncs
- Check the Google Drive icon in your system tray

---

## Donate
Hearth is free forever. If it saves you money on server hosting or just makes your gaming sessions better, consider buying me a coffee.

[☕ buymeacoffee.com/hearthapp](https://buymeacoffee.com/hearthapp)

---

## License
MIT License — free to use, modify, and distribute.

Built by Chester Houston · hearthforpc@gmail.com
