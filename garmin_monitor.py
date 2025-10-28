#!/usr/bin/env python3
"""
Garmin Connect Monitor - Polls for new data and sends updates to Poke API
"""

import argparse
import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv
from garminconnect import Garmin

# Load environment variables
load_dotenv()

# Configuration
GARMIN_EMAIL = os.getenv('GARMIN_EMAIL')
GARMIN_PASSWORD = os.getenv('GARMIN_PASSWORD')
POKE_API_KEY = os.getenv('POKE_API_KEY')
STATE_FILE = Path(__file__).parent / 'last_check.json'
POKE_API_URL = 'https://poke.com/api/v1/inbound-sms/webhook'


def log(message: str):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def load_state() -> Dict[str, Any]:
    """Load the last check state from file"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading state file: {e}")
    
    return {
        'last_activity_id': None,
        'last_daily_stats_date': None,
        'last_sleep_id': None
    }


def save_state(state: Dict[str, Any]):
    """Save the current state to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving state file: {e}")


def send_to_poke(message: str, test_mode: bool = False) -> bool:
    """Send a message to the Poke API"""
    if test_mode:
        log(f"[TEST MODE] Would send to Poke: {message}")
        return True
    
    try:
        response = requests.post(
            POKE_API_URL,
            headers={
                'Authorization': f'Bearer {POKE_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={'message': message},
            timeout=10
        )
        
        if response.status_code == 200:
            log(f"✓ Sent to Poke: {message}")
            return True
        else:
            log(f"✗ Poke API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        log(f"✗ Error sending to Poke: {e}")
        return False


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def format_distance(meters: float) -> str:
    """Format meters into km"""
    km = meters / 1000
    return f"{km:.1f}km"


def format_activity(activity: Dict[str, Any]) -> str:
    """Format an activity into a readable message"""
    name = activity.get('activityName', 'Activity')
    activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
    
    # Get duration
    duration_sec = activity.get('duration') or 0
    duration_str = format_duration(int(duration_sec))
    
    # Get distance
    distance = activity.get('distance')
    distance_str = f", {format_distance(distance)}" if distance else ""
    
    # Get average heart rate
    avg_hr = activity.get('averageHR')
    hr_str = f", {int(avg_hr)} avg HR" if avg_hr else ""
    
    # Get calories
    calories = activity.get('calories')
    cal_str = f", {int(calories)} cal" if calories else ""
    
    return f"Completed {name} ({duration_str}{distance_str}{hr_str}{cal_str})"


def format_daily_stats(stats: Dict[str, Any]) -> str:
    """Format daily stats into a readable message"""
    steps = stats.get('totalSteps') or 0
    calories = stats.get('totalKilocalories') or 0
    distance = stats.get('totalDistanceMeters') or 0
    
    parts = [f"Daily: {steps:,} steps"]
    
    if calories:
        parts.append(f"{int(calories)} cal")
    
    if distance:
        parts.append(format_distance(distance))
    
    # Add heart rate if available
    resting_hr = stats.get('restingHeartRate')
    if resting_hr:
        parts.append(f"RHR {int(resting_hr)}")
    
    return ", ".join(parts)


def format_sleep(sleep_data: Dict[str, Any]) -> str:
    """Format sleep data into a readable message"""
    # Sleep duration in seconds
    sleep_seconds = sleep_data.get('sleepTimeSeconds') or 0
    duration_str = format_duration(int(sleep_seconds))
    
    # Sleep quality/score
    score = sleep_data.get('sleepScores', {}).get('overall', {}).get('value')
    score_str = f" ({int(score)}% quality)" if score else ""
    
    return f"Sleep: {duration_str}{score_str}"


def check_for_updates(client: Garmin, state: Dict[str, Any]) -> List[str]:
    """Check for new data and return messages to send"""
    messages = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Check for new activities
        activities = client.get_activities(0, 10)  # Get last 10 activities
        
        if activities:
            # Get the most recent activity
            latest_activity = activities[0]
            latest_activity_id = latest_activity.get('activityId')
            
            if latest_activity_id != state.get('last_activity_id'):
                # New activity detected
                message = format_activity(latest_activity)
                messages.append(message)
                state['last_activity_id'] = latest_activity_id
        
    except Exception as e:
        log(f"Error fetching activities: {e}")
    
    try:
        # Check for daily stats
        daily_stats = client.get_stats(today)
        
        if daily_stats and state.get('last_daily_stats_date') != today:
            # Only send if we have meaningful data (more than 100 steps)
            steps = daily_stats.get('totalSteps') or 0
            if steps > 100:
                message = format_daily_stats(daily_stats)
                messages.append(message)
                state['last_daily_stats_date'] = today
        
    except Exception as e:
        log(f"Error fetching daily stats: {e}")
    
    try:
        # Check for sleep data
        sleep_data = client.get_sleep_data(today)
        
        if sleep_data and 'dailySleepDTO' in sleep_data:
            sleep_summary = sleep_data['dailySleepDTO']
            sleep_id = sleep_summary.get('id')
            
            if sleep_id and sleep_id != state.get('last_sleep_id'):
                # New sleep data detected
                message = format_sleep(sleep_summary)
                messages.append(message)
                state['last_sleep_id'] = sleep_id
        
    except Exception as e:
        log(f"Error fetching sleep data: {e}")
    
    return messages


def main():
    """Main monitoring function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Monitor Garmin Connect for new data and send updates to Poke API'
    )
    parser.add_argument(
        '--test',
        '--dry-run',
        dest='test_mode',
        action='store_true',
        help='Test mode: fetch data but do not send to Poke API'
    )
    args = parser.parse_args()
    
    if args.test_mode:
        log("⚠️  Running in TEST MODE - no messages will be sent to Poke")
    
    # Validate configuration
    if not GARMIN_EMAIL or not GARMIN_PASSWORD:
        log("✗ Error: GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env")
        sys.exit(1)
    
    if not args.test_mode and not POKE_API_KEY:
        log("✗ Error: POKE_API_KEY must be set in .env")
        sys.exit(1)
    
    # Load state
    state = load_state()
    
    try:
        # Initialize Garmin client
        log("Authenticating with Garmin Connect...")
        client = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        client.login()
        log("✓ Authentication successful")
        
        # Check for updates
        log("Checking for new data...")
        messages = check_for_updates(client, state)
        
        if messages:
            log(f"Found {len(messages)} update(s)")
            
            # Send each message to Poke
            for message in messages:
                send_to_poke(message, test_mode=args.test_mode)
            
            # Save updated state (skip in test mode to allow re-testing)
            if not args.test_mode:
                save_state(state)
            else:
                log("[TEST MODE] State file not updated - you can run test again to see the same data")
        else:
            log("No new data")
        
    except Exception as e:
        log(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

