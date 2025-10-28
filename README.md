# Garmin-Poke Integration

Automatically monitor Garmin Connect for new data (activities, daily stats, sleep) and send formatted summaries to the Poke API.

## Features

- 🏃 Tracks new activities/workouts with details (duration, distance, heart rate, calories)
- 📊 Monitors daily stats (steps, calories, distance, resting heart rate)
- 😴 Detects new sleep data with duration and quality scores
- 📱 Sends human-readable summaries to Poke API
- 🔄 Runs every minute via cron job
- 💾 State tracking to avoid duplicate notifications

## Setup

### 1. Install Dependencies

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Dependencies are already installed if you see a .venv directory
# To reinstall or set up on a new machine:
uv sync
```

### 2. Configure Credentials

Create a `.env` file with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```
GARMIN_EMAIL=your-garmin-email@example.com
GARMIN_PASSWORD=your-garmin-password
POKE_API_KEY=your-poke-api-key
```

### 3. Test Manually

#### Test Mode (Recommended First)

Run the monitor in test mode to verify Garmin authentication and data fetching without sending to Poke:

```bash
uv run garmin_monitor.py --test
```

You should see output like:
```
[2025-10-28 10:00:00] ⚠️  Running in TEST MODE - no messages will be sent to Poke
[2025-10-28 10:00:00] Authenticating with Garmin Connect...
[2025-10-28 10:00:01] ✓ Authentication successful
[2025-10-28 10:00:01] Checking for new data...
[2025-10-28 10:00:02] Found 1 update(s)
[2025-10-28 10:00:02] [TEST MODE] Would send to Poke: Completed Morning Run (30m, 5.2km, 145 avg HR, 320 cal)
[2025-10-28 10:00:02] [TEST MODE] State file not updated - you can run test again to see the same data
```

Note: In test mode, the state file is not updated, so you can run the test multiple times to see the same data.

#### Live Mode

Once test mode works, run without the `--test` flag to actually send to Poke:

```bash
uv run garmin_monitor.py
```

You should see output like:
```
[2025-10-28 10:00:00] Authenticating with Garmin Connect...
[2025-10-28 10:00:01] ✓ Authentication successful
[2025-10-28 10:00:01] Checking for new data...
[2025-10-28 10:00:02] Found 1 update(s)
[2025-10-28 10:00:02] ✓ Sent to Poke: Completed Morning Run (30m, 5.2km, 145 avg HR, 320 cal)
```

### 4. Set Up Cron Job

To run the monitor every minute, add it to your crontab:

```bash
crontab -e
```

Add this line (adjust the path if needed):

```cron
* * * * * cd /Users/orarbel/Development/garmin-poke && /Users/orarbel/Development/garmin-poke/.venv/bin/python garmin_monitor.py >> /Users/orarbel/Development/garmin-poke/garmin_monitor.log 2>&1
```

This will:
- Run every minute (`* * * * *`)
- Change to the project directory
- Execute the script using the virtual environment's Python
- Log output to `garmin_monitor.log` for debugging

Save and exit. The cron job will start running automatically.

### 5. Verify Cron Job

Check that the cron job is running:

```bash
# View the last few log entries
tail -f garmin_monitor.log
```

You should see new entries every minute.

## Message Format Examples

The script sends concise, readable messages to Poke:

**Activities:**
- `Completed Morning Run (30m, 5.2km, 145 avg HR, 320 cal)`
- `Completed Cycling (1h 15m, 25.3km, 138 avg HR)`
- `Completed Weight Training (45m, 250 cal)`

**Daily Stats:**
- `Daily: 10,245 steps, 2,500 cal, 8.2km, RHR 58`
- `Daily: 5,123 steps, 1,800 cal, 4.1km`

**Sleep:**
- `Sleep: 7h 23m (85% quality)`
- `Sleep: 6h 45m`

## State Management

The script maintains a `last_check.json` file to track:
- Last processed activity ID
- Last daily stats date
- Last sleep session ID

This ensures you only receive notifications for new data, not duplicates.

## Troubleshooting

### Authentication Errors

If you see authentication errors:
1. Verify your Garmin credentials in `.env`
2. Try logging into Garmin Connect web to ensure your account is accessible
3. Check if Garmin is requiring a CAPTCHA (may need to login via browser first)

### No Data Detected

If the script runs but finds no data:
1. Check that you have recent activities/stats in Garmin Connect
2. Delete `last_check.json` to reset state and force a fresh check
3. The script only sends daily stats if you have more than 100 steps

### Poke API Errors

If messages aren't reaching Poke:
1. Verify your `POKE_API_KEY` in `.env`
2. Check the log output for HTTP error codes
3. Test the API manually with curl:

```bash
curl -X POST https://poke.com/api/v1/inbound-sms/webhook \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message"}'
```

### Viewing Logs

```bash
# View all logs
cat garmin_monitor.log

# Follow logs in real-time
tail -f garmin_monitor.log

# View last 50 lines
tail -n 50 garmin_monitor.log
```

### Stopping the Cron Job

To stop the automatic monitoring:

```bash
crontab -e
# Comment out or delete the line with garmin_monitor.py
# Save and exit
```

## Development

### Test Mode

The script supports a test/dry-run mode for development and debugging:

```bash
# Using --test flag
uv run garmin_monitor.py --test

# Or using --dry-run (same as --test)
uv run garmin_monitor.py --dry-run
```

In test mode:
- ✅ Authenticates with Garmin Connect
- ✅ Fetches all data (activities, daily stats, sleep)
- ✅ Formats messages
- ❌ Does NOT send messages to Poke API
- ❌ Does NOT update state file (so you can test multiple times with same data)
- ❌ Does NOT require `POKE_API_KEY` in `.env`

This is useful for:
- Testing Garmin authentication
- Verifying data formatting
- Debugging without spamming Poke
- Developing new features

### Project Structure

```
garmin-poke/
├── garmin_monitor.py    # Main monitoring script
├── pyproject.toml       # Project dependencies (managed by uv)
├── uv.lock              # Locked dependencies
├── .env                 # Your credentials (not in git)
├── .env.example         # Template for credentials
├── .gitignore           # Git ignore rules
├── last_check.json      # State file (auto-generated)
├── garmin_monitor.log   # Log file (auto-generated)
└── README.md            # This file
```

### Modifying Check Frequency

Edit the cron schedule in `crontab -e`:

- Every 5 minutes: `*/5 * * * *`
- Every 15 minutes: `*/15 * * * *`
- Every hour: `0 * * * *`
- Once per day at 9am: `0 9 * * *`

### Adding More Data Types

The `garminconnect` library supports many more data types:
- Body composition
- Heart rate variability
- Training status
- Stress levels
- And more...

See the [garminconnect documentation](https://github.com/cyberjunky/python-garminconnect) for available methods.

## License

MIT

