# Weekly snapshot run with launchd

Runs `gradprog snapshot run` every Sunday at 20:00 (docs/spec/07_snapshots.md §10.1). Nothing here is installed automatically.

## 1. Contact email (outside the repository)

launchd does not read `~/.zshrc`. `run-snapshot.sh` reads the contact email from `~/.config/gradprog/env`:

```bash
mkdir -p ~/.config/gradprog
printf 'GRADPROG_CONTACT_EMAIL=you@example.com\n' > ~/.config/gradprog/env
chmod 600 ~/.config/gradprog/env
```

Replace `you@example.com` with your address. Only `GRADPROG_CONTACT_EMAIL` is read from this file.

## 2. Install the job

```bash
REPO_DIR="$(pwd)"   # run from the repository root
sed "s#__REPO_DIR__#${REPO_DIR}#g" ops/launchd/com.gradprog.snapshot.plist.template > ~/Library/LaunchAgents/com.gradprog.snapshot.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.gradprog.snapshot.plist
launchctl print gui/$(id -u)/com.gradprog.snapshot | head -20
```

Run once by hand to check the setup:

```bash
launchctl kickstart gui/$(id -u)/com.gradprog.snapshot
```

Uninstall:

```bash
launchctl bootout gui/$(id -u)/com.gradprog.snapshot
rm ~/Library/LaunchAgents/com.gradprog.snapshot.plist
```

## 3. Time zone (时区)

`StartCalendarInterval` uses the Mac's **system time zone**. With the Mac set to Asia/Tokyo (东京时区) the job runs every Sunday 20:00 Tokyo time (`Weekday` 0 = Sunday, `Hour` 20, `Minute` 0). If the Mac is asleep at that time, launchd runs the job when it wakes.

## 3a. Sleep during the run (睡眠)

`run-snapshot.sh` runs the job under `caffeinate -i`, which blocks **idle** sleep while the run lasts. It does **not** prevent lid-close sleep (合盖睡眠), sleep forced by a low battery, or sleep you start yourself. On Sunday evening keep the Mac open (or on an external display) and preferably on power. A scheduled wake (`pmset schedule`) does not help with the lid closed: the Mac only dark-wakes and goes back to sleep. The 09:00 runs on 2026-10-11 (battery, 11%) and 2026-10-18 (lid closed) took 65 and 109 minutes for this reason, which is why the job moved to 20:00.

The log records the power state at the start and end of each run, the run time, and how many times the Mac entered sleep during it; a line starting with `WARNING:` means it slept or the run took longer than 15 minutes.

Before requesting anything, the run checks that at least one of the sites is reachable (a TCP connection to port 443, no HTTP request). If none is, it prints `run skipped: network unavailable …`, exits with code 75 and writes nothing; the next scheduled run tries again.

## 4. Logs

`data/snapshots/logs/launchd.out.log` and `launchd.err.log` (not tracked by git). Each run also writes `data/snapshots/reports/run-<run_id>.md`.
