# Hearth v1.5
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
3. Double-click Hearth.exe to run it — Windows may show a warning saying "Unknown publisher." Click **More info** then **Run anyway.** This warning appears because Hearth doesn't have a paid security certificate yet. The source code is fully public if you want to verify it.
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

> **Before you do this:** You need to have at least one saved world in your game. Just launching the game is not enough — you must create a world, load into it, and then exit. Hearth can only see worlds that have been saved to your PC. If you skip this step your world list will be empty.

1. In Hearth, find your game in the list
2. You will see your worlds listed underneath
3. Check the box next to the world you want to share
4. Hearth will push it to your Google Drive folder automatically
5. Your friend opens Hearth — your world will appear under their name automatically within seconds
6. Your friend can now download it and play

---

## How Automatic Sync Works

Hearth keeps everyone in sync without any manual steps:

- **When Hearth opens** — it immediately pulls any newer worlds from Drive before you do anything
- **When a game is detected launching** — Hearth pulls the latest version of all shared worlds before you reach the main menu
- **While Hearth is running** — it checks Drive every 10 seconds and pulls any changes automatically
- **When you close a game** — Hearth waits 20 seconds then pushes your save to Drive and clears the lock

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

---

### Getting your Valheim worlds back from Steam Cloud

If you have existing Valheim worlds but Hearth can't see them, Steam Cloud is likely holding your saves. Here's how to get them back:

1. Open Steam
2. Right-click Valheim in your library → click **Properties**
3. Click **General**
4. Uncheck **"Keep game saves in the Steam Cloud"**
5. Launch Valheim — Steam may ask what to do with your saves. If it asks, choose **"Keep the local files"** or **"Download from Steam Cloud"** depending on which copy you want to keep
6. Load into your world once so Valheim writes the save to your PC
7. Exit Valheim completely
8. Open Hearth — your worlds should now appear

If Steam does not ask and your worlds are still missing after step 7, open File Explorer and check this folder:
```
C:\Users\[YourName]\AppData\LocalLow\IronGate\Valheim\worlds_local
```
You should see `.fwl` files with your world names. If the folder is empty, your saves are still on Steam's servers. In that case turn Steam Cloud back on, launch Valheim, exit, turn it back off, then repeat the steps above.

**Everyone in your group must turn off Steam Cloud**, otherwise Valheim saves to Steam's servers instead of your PC and Hearth cannot see them.

---

## Icarus Players — Read This

Icarus uses Steam Cloud by default. Hearth cannot see Steam Cloud saves. You need to turn off Steam Cloud for Icarus:

1. Open Steam
2. Right-click Icarus in your library
3. Click Properties
4. Click General
5. Uncheck "Keep game saves in the Steam Cloud"

**Both you and your friend must do this.** If one person has it on and the other has it off, Icarus will load from Steam's servers instead of the file Hearth synced.

Also make sure you have actually created a prospect and loaded into it at least once before Hearth can detect it.

---

## Enshrouded Players — Read This

Enshrouded saves to Steam's servers by default. Hearth cannot see those files. You need to turn off Steam Cloud for Enshrouded:

1. Open Steam
2. Right-click Enshrouded in your library
3. Click Properties
4. Click General
5. Uncheck "Keep game saves in the Steam Cloud"

**Both you and your friend must do this.** If one person has it on and the other has it off, it will not work.

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

The game will appear in your worlds list like any other supported game.

---

## Hiding Games You Don't Play

1. Click **Game** in the menu bar
2. Click **Show / Hide Games**
3. Uncheck any games you want to hide
4. Click Save

---

## Backups
Hearth automatically backs up your save files before every sync. You can find your backups at:
`C:\Users\[YourName]\Hearth_Backups\`

---

## Something Not Working?

**I can't find my HearthSync folder in Hearth**
- Make sure Google Drive for Desktop is installed and set to Mirror Files mode
- Look for a drive letter like G: or F: in File Explorer under "This PC"
- The HearthSync folder should be inside that drive

**My world isn't showing up in Hearth**
- You must create a world and fully load into it at least once — just launching the game to the main menu is not enough for some games (Valheim in particular)
- For Valheim and Enshrouded: make sure Steam Cloud is turned off (see the game-specific sections above)

**My game isn't in the list**
- Click Game → Add Game to add any game manually

**The save path is wrong for my setup**
- Click the **Config** button next to the game name in Hearth
- Browse to your actual save folder and select it

**The lock is stuck and I can't sync**
- In Hearth, go to Help then Unlock All
- Or find the HearthSync folder in your Google Drive and delete the file called hearth.lock

**Windows says Hearth is dangerous**
- Click "More info" then "Run anyway"
- This happens because Hearth doesn't have a paid security certificate yet
- The full source code is public at github.com/hearthforpc-oss/Hearth if you want to verify it

---

## Donate
Hearth is free forever. If it saves you the cost of a game server or just makes gaming with your friends easier, consider buying me a coffee.

https://buymeacoffee.com/hearthapp

---

## License
MIT License — free to use, share, and modify.

Built by Chester Houston - hearthforpc@gmail.com
