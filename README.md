# Hearth v1.0
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
- Icarus
- Valheim
- Terraria
- Terraria (tModLoader)
- Core Keeper
- Enshrouded
- Sons of the Forest

---

5 obscure scanners flag it as a false positive, source code is public on GitHub, here's the link to verify it yourself.
https://virustotal.com/gui/file/cbd5ef008ae7e8434691a5c9e10e166fb00942db60402e7bf6eefba466ce5b3e/detection

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
4. When it asks how to sync files, choose **Mirror Files** — this is important, Stream Files will not work
5. After it finishes, Google Drive will create a new folder on your PC that looks like a regular folder. On most computers it shows up as a drive letter like G: or F: in File Explorer — look for it under "This PC"

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
2. Click the link to accept
3. Open Google Drive on your PC (the folder you set up in Step 1)
4. The HearthSync folder should now appear inside your Google Drive folder on your PC
5. If you don't see it yet, wait a minute and check again

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

> **Before you do this:** Launch your game at least once and then close it. Hearth needs the game to create its save files first. If you skip this step your world list will be empty.

1. In Hearth, find your game in the list
2. You will see your worlds listed underneath
3. Check the box next to the world you want to share
4. Hearth will push it to your Google Drive folder automatically
5. Your friend opens Hearth and clicks **Sync Now** — your world will appear under your name
6. Your friend can now download it and play

---

## Playing Together

**When you want to play solo while your friend is offline:**
1. Open Hearth and click **Sync Now** to get the latest save
2. Launch your game and play
3. When you close the game, Hearth automatically syncs your progress back to Drive
4. Your friend can then sync and pick up where you left off

**When you play together at the same time:**
- One person hosts the game, others join as normal
- Hearth handles the save file when the host closes the game

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
- Launch the game at least once so it creates your save files
- For Enshrouded and Core Keeper: make sure Steam Cloud is turned off

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
