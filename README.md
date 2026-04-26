# Hearth v1.6
**Play the same game world with your friends — even when you're on different schedules.**

Hearth is a free app that automatically shares your game save files with your friends through Google Drive. When you stop playing, your friend can pick up right where you left off — no dedicated server needed.

**Free. Open source. Your save files stay in your own Google Drive.**

---

## Is Hearth safe?

Yes. Here is exactly how it works:

Hearth uses Google Drive folder sharing — the same way you would share a document with a friend or family member. You create one folder called HearthSync and share it with the people you play with.

- Your friend only gets access to that one folder. Not your email, not your other files, not your Google account.
- Hearth never asks for your Google password. It reads and writes files through Google's own app on your PC.
- Your save files never go to anyone else's servers. They live in your own Google Drive.
- Hearth is open source — every line of code is public on this page. Anyone can read exactly what it does.

**Hearth is designed for people you already play games with — friends, family, your cousin. It is not for sharing with strangers.**

---

## Supported Games

**Verified working:**
- Icarus
- Valheim
- Terraria
- Terraria (tModLoader)
- Core Keeper
- Enshrouded
- Sons of the Forest

**Unverified (may work):**
- 7 Days to Die
- The Forest
- Grounded
- Astroneer
- V Rising
- Don't Starve Together
- Stardew Valley

**Any game not on this list** — use Game → Add Game to add it manually.

---

## What You Need
- A Windows PC
- A Google account (free at google.com)
- The people you play with also need a Google account
- Google Drive for Desktop installed and set to **Mirror Files** mode

That's it. No coding. No servers. No technical knowledge required.

---

## Setup — Do This Once

### Step 1 — Download and install Google Drive for Desktop

1. Go to **drive.google.com/drive/downloads** in your browser
2. Click the download button and run the installer
3. Sign in with your Google account when it asks
4. After it installs, find the Google Drive icon in your system tray (bottom right near the clock) and click it
5. Click the **gear icon** in the top right of the popup, then click **Preferences**
6. In the Preferences window, click **Google Drive** on the left side
7. Select **Mirror Files** — this is important, Stream Files will not work
8. Click Save and let it finish syncing
9. Google Drive will create a new folder on your PC that looks like a regular drive. Look for it under "This PC" in File Explorer — it will show up as a drive letter like G: or F:

> **Important:** Hearth requires Google Drive to be running whenever you use it. If you close Google Drive from the system tray, Hearth will warn you that the Drive folder is unreachable. Just reopen Google Drive and Hearth will recover automatically.

### Step 2 — Create a shared folder

**One person in your group does this. Everyone else skips to Step 3.**

1. Open your Google Drive folder in File Explorer (the one you just set up)
2. Right-click inside it and create a new folder called **HearthSync**
3. Go to drive.google.com in your browser
4. Find the HearthSync folder, right-click it, and click **Share**
5. Type in your friend's Google email address and make sure they have **Editor** access
6. Click Send — your friend will get an email invitation
7. Your friend clicks the link in the email to accept

### Step 3 — Accept the shared folder (everyone except the person who created it)

1. Check your email for an invitation from Google Drive
2. Click the link in the email to accept
3. Go to **drive.google.com** in your browser
4. In the left sidebar click **Shared with me**
5. Find the HearthSync folder
6. Right-click it and click **Add shortcut to Drive**
7. Choose **My Drive** and click Add
8. Now open your Google Drive folder on your PC — HearthSync should appear within a minute or two
9. If you don't see it yet, wait a minute and check again

### Step 4 — Download and run Hearth

1. Go to **github.com/hearthforpc-oss/Hearth/releases**
2. Click **Hearth.exe** to download it
3. Double-click Hearth.exe to run it — Windows may show a warning saying "Unknown publisher." Click **More info** then **Run anyway.** This warning appears because Hearth doesn't have a paid security certificate. The source code is fully public if you want to verify it.
4. Hearth will open and ask you to fill in some information

### Step 5 — Set up Hearth

Fill in these fields:

**Your name** — just type your first name or nickname. Your friends will see this in the app.

**Steam ID** — only needed if you play Icarus or Core Keeper. For all other games, leave this blank.
- To find your Steam ID: open Steam, click your profile name at the top right, click View Profile, then look at the URL in your browser. The long number at the end is your Steam ID.
- Example: steamcommunity.com/profiles/**76561198292066021**

**Drive folder** — click Browse and find your HearthSync folder. It will be inside your Google Drive folder on your PC. Select the HearthSync folder and click OK.

Click **Save** when done.

### Step 6 — Share your world

> **Before you do this:** You need to have at least one saved world in your game. Just launching the game is not enough — you must create a world, load into it, and then exit. Hearth can only see worlds that have been saved to your PC.

1. In Hearth, find your game in the list
2. You will see your worlds listed underneath
3. Check the box next to the world you want to share
4. Hearth will push it to your Google Drive folder automatically
5. Your friend opens Hearth — your world will appear under their name

> **World naming tip:** Make sure your world name has no spaces at the beginning or end, and avoid special characters like `\ / : * ? " < > |`. Hearth will warn you at share time if there's a problem.

### Step 7 — Opt into a friend's world

When a friend shares a world, it appears in your Hearth under their name marked as **Available**. It will not sync automatically until you opt in.

1. Find their world in your Hearth list
2. Check the box next to it to participate
3. Hearth will pull the latest save and keep it in sync going forward

This means you are always in control of which worlds you sync. Nothing downloads without your permission.

---

## How Automatic Sync Works

Hearth keeps everyone in sync without any manual steps:

- **When Hearth opens** — it checks Drive for any newer worlds and pulls them before you do anything
- **When a game is detected launching** — Hearth locks all shared worlds and pulls the latest version before you reach the main menu
- **While you're in game** — Hearth backs up your save locally every 25 minutes
- **When you close a game** — Hearth waits for your save file to finish writing, then pushes it to Drive and clears the lock
- **Every 10 minutes** — Hearth checks for any stale locks on your own worlds and clears them if the game is no longer running
- **Every 30 minutes** — Hearth checks that your Google Drive folder is still accessible and warns you if it isn't

You should never need to click Sync Now for normal play. It is there as a manual override if you need it.

---

## Playing Together

**When you want to play solo while your friend is offline:**
1. Open Hearth — it will pull the latest save automatically
2. Launch your game and play
3. When you close the game, Hearth automatically syncs your progress back to Drive
4. Your friend opens Hearth when they're ready — it pulls your save automatically

**When you play together at the same time:**
- One person hosts the game, others join as normal
- Hearth handles the save file when the host closes the game

---

## Valheim Players — Read This

Valheim does not create any save files until you actually create a world and load into it. Just launching the game and reaching the main menu is not enough.

Before Hearth can see your Valheim worlds, you must:

1. Launch Valheim
2. Click **Start Game**
3. Create a new world (or load an existing one)
4. Wait until you are fully loaded into the game
5. Exit back to the main menu, then quit Valheim completely

After that, Hearth will find your world automatically.

**Everyone in your group must turn off Steam Cloud for Valheim**, otherwise Valheim saves to Steam's servers instead of your PC and Hearth cannot see them.

### Getting your Valheim worlds back from Steam Cloud

If you have existing Valheim worlds but Hearth can't see them, Steam Cloud is likely holding your saves. Here's how to get them back:

1. Open Steam
2. Right-click Valheim in your library → click **Properties**
3. Click **General**
4. Uncheck **"Keep game saves in the Steam Cloud"**
5. Launch Valheim — if it asks what to do with your saves, choose **"Keep the local files"**
6. Load into your world once so Valheim writes the save to your PC
7. Exit Valheim completely
8. Open Hearth — your worlds should now appear

If your worlds are still missing, open File Explorer and check:
```
C:\Users\[YourName]\AppData\LocalLow\IronGate\Valheim\worlds_local
```
If the folder is empty, your saves are still on Steam's servers. Turn Steam Cloud back on, launch Valheim, exit, turn it back off, then repeat the steps above.

---

## Icarus Players — Read This

Icarus uses Steam Cloud by default. Hearth cannot see Steam Cloud saves. Turn it off:

1. Open Steam
2. Right-click Icarus in your library → Properties → General
3. Uncheck **"Keep game saves in the Steam Cloud"**

**Both you and your friend must do this.** Also make sure you have created a prospect and fully loaded into it at least once before Hearth can detect it.

---

## Enshrouded Players — Read This

Enshrouded saves to Steam's servers by default. Turn it off:

1. Open Steam
2. Right-click Enshrouded in your library → Properties → General
3. Uncheck **"Keep game saves in the Steam Cloud"**

**Both you and your friend must do this.**

---

## Sons of the Forest Players — Read This

Before Hearth can sync Sons of the Forest saves, everyone in your group must have hosted at least one multiplayer lobby. This creates the required save folder on their machine.

1. Launch Sons of the Forest
2. Go to Multiplayer → Host Game → start any session
3. Exit the game
4. Now Hearth can sync your multiplayer saves

---

## Tray Icon
When you close the Hearth window it keeps running in your system tray (bottom right corner of your screen, near the clock). Click the Hearth icon to bring the window back.

| Icon Color | What It Means |
|------------|--------------|
| Orange | Hearth is running normally |
| Green | Currently syncing |
| Blue | An update is available |
| Red | Something needs attention |

---

## Adding a Game Not on the List

Hearth supports any game that saves to a local folder. To add one:

1. Click **Game** in the menu bar
2. Click **Add Game**
3. Hearth will scan your PC for save folders and show you what it finds
4. Click the game you want to add, or browse manually if it isn't listed
5. Confirm the file extension and click Add Game

---

## Hiding Games You Don't Play

1. Click **Game** in the menu bar
2. Click **Show / Hide Games**
3. Uncheck any games you want to hide
4. Click Save

---

## Backups
Hearth automatically backs up your save files before every sync and every 25 minutes while you're in game. You can find your backups at:
```
C:\Users\[YourName]\Hearth_Backups\
```

---

## Something Not Working?

**Hearth says the Drive folder is unreachable**
- Google Drive is not running. Find the Google Drive app and open it from your Start menu or system tray.
- Once Google Drive is running the warning in Hearth will clear automatically.

**I can't find my HearthSync folder in Hearth**
- Make sure Google Drive for Desktop is installed and set to Mirror Files mode
- Look for a drive letter like G: or F: in File Explorer under "This PC"
- The HearthSync folder should be inside that drive

**My world isn't showing up in Hearth**
- You must create a world and fully load into it at least once before Hearth can see it
- For Valheim and Enshrouded: make sure Steam Cloud is turned off (see the game-specific sections above)

**A friend's world shows as Available but won't sync**
- Check the box next to their world to opt in — worlds from other players don't sync automatically until you participate

**My world name has a warning at share time**
- Rename the world in-game to remove any spaces at the start or end and avoid special characters
- Then try sharing again

**My game isn't in the list**
- Click Game → Add Game to add any game manually

**The save path is wrong for my setup**
- Click the **Config** button next to the game name in Hearth
- Browse to your actual save folder and select it

**The lock is stuck and I can't sync**
- Hearth automatically clears stale locks every 10 minutes if the game is no longer running
- Or go to Help → Unlock All to clear it manually
- Hearth will only ever clear locks that belong to you — it will never clear a lock that belongs to someone else in your group

**Windows says Hearth is dangerous**
- Click "More info" then "Run anyway"
- This happens because Hearth doesn't have a paid security certificate
- The full source code is public at github.com/hearthforpc-oss/Hearth if you want to verify it

---

## Donate
Hearth is free forever. If it saves you the cost of a game server or just makes gaming with your friends easier, consider buying us a coffee.

https://buymeacoffee.com/hearthapp

---

## License
MIT License — free to use, share, and modify.

hearthforpc@gmail.com
