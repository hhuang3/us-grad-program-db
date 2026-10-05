# Weekly snapshot run with launchd

Runs `gradprog snapshot run` every Monday at 07:00 (docs/spec/07_snapshots.md §10.1). Nothing here is installed automatically.

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

`StartCalendarInterval` uses the Mac's **system time zone**. With the Mac set to Asia/Tokyo (东京时区) the job runs at 07:00 Tokyo time. If the Mac is asleep at that time, launchd runs the job when it wakes.

## 4. Logs

`data/snapshots/logs/launchd.out.log` and `launchd.err.log` (not tracked by git). Each run also writes `data/snapshots/reports/run-<run_id>.md`.
