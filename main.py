import json
import os
import requests
import csv
from flask import Flask, request, jsonify
from datetime import datetime
import re
from threading import Timer

app = Flask("__main__")

discord_webhook_url = os.getenv("WEBHOOK_URL")
api_key = os.getenv("API_KEY")

MAX_CHAT_LOGS = 50
chat_buffer = []
sent_messages = set()
player_data = {}
join_logs = []
leave_logs = []
active_players = {}
commands = {
    "urdone": "send_csv",
    "thepurgeishere": "shutdown_server"
}

def decode_message(message):
    """Decode a message by replacing sequences of '#' with '[REDACTED]'."""
    return re.sub(r'#+', '[REDACTED]', message)

def add_to_chat_buffer(chat_log):
    """Add a chat log to the rolling buffer, maintaining size limit."""
    global chat_buffer
    chat_buffer.append(chat_log)
    if len(chat_buffer) > MAX_CHAT_LOGS:
        chat_buffer.pop(0)

def generate_csv(chat_logs, filename="chat_logs.csv"):
    """Generate a CSV file from chat logs."""
    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Message"])
            for log in chat_logs:
                writer.writerow([log["timestamp"], log["content"]])
        print(f"CSV generated successfully: {filename}")
        return filename
    except Exception as e:
        print(f"Error generating CSV: {e}")
        return None

def handle_command(command, place_id, server_id):
    """Handle special commands from chat."""
    print(f"Handling command: {command}")
    if command == "send_csv":
        if chat_buffer:
            csv_filename = generate_csv(chat_buffer)
            if csv_filename:
                send_csv_to_discord(csv_filename)
        else:
            print("No chat logs available to generate a CSV.")
    elif command == "shutdown_server":
        shutdown_server(place_id, server_id)

def send_csv_to_discord(csv_filename):
    """Send a CSV file to Discord."""
    try:
        with open(csv_filename, "rb") as file:
            files = {"file": (csv_filename, file)}
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.post(discord_webhook_url, files=files, headers=headers)
            response.raise_for_status()
            print(f"CSV file sent to Discord successfully. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending CSV to Discord: {e}")
    except Exception as e:
        print(f"Unexpected error sending CSV: {e}")

def shutdown_server(place_id, server_id):
    """Simulate shutting down a server."""
    print(f"Shutting down server {server_id} for place {place_id}.")
    # Send shutdown message to Discord
    shutdown_message = "The server has been shut down due to 'The Purge' command."
    discord_payload = {"content": shutdown_message}
    try:
        response = requests.post(discord_webhook_url, json=discord_payload, headers={"Authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        print("Shutdown message sent to Discord.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending shutdown message to Discord: {e}")

@app.route('/', methods=['POST'])
def root():
    try:
        data = request.json

        # Extract the data from the incoming payload
        place_id = data.get('placeId', 'N/A')
        server_id = data.get('serverId', 'N/A')
        private_server_id = data.get('privateServerId', 'N/A')
        private_server_url = data.get('privateServerUrl', 'N/A')

        # Update player data
        player_list = data.get('playerData', '').split('\n')
        global player_data, join_logs, leave_logs, active_players

        for player_info in player_list:
            if " (" in player_info:
                name, display_name = player_info.split(" (")
                display_name = display_name.rstrip(")")
                player_data[name] = display_name

        # Process join and leave logs
        join_leave_logs = data.get('joinLeaveLogs', '').split('\n')
        for log in join_leave_logs:
            if "joined the game" in log:
                match = re.match(r"(.+) \((.+)\) joined the game\.", log)
                if match:
                    name, display_name = match.groups()
                    if name not in active_players:
                        timestamp = datetime.utcnow().isoformat() + "Z"
                        active_players[name] = timestamp
                        join_logs.append(f"{log} at {timestamp}")
            elif "left the game" in log:
                match = re.match(r"(.+) \((.+)\) left the game\.", log)
                if match:
                    name, _ = match.groups()
                    if name in active_players:
                        timestamp = datetime.utcnow().isoformat() + "Z"
                        del active_players[name]
                        leave_logs.append(f"{log} at {timestamp}")

        # Process chat logs
        chat_logs = data.get('chatLogs', [])
        new_chat_logs = []

        for chat_log in chat_logs:
            decoded_message = decode_message(chat_log)
            if decoded_message not in sent_messages:
                timestamp = datetime.utcnow().isoformat() + "Z"
                add_to_chat_buffer({
                    "content": decoded_message,
                    "timestamp": timestamp
                })
                new_chat_logs.append({
                    "content": decoded_message,
                    "timestamp": timestamp
                })
                sent_messages.add(decoded_message)

                # Check for commands in the message
                for command in commands.keys():
                    if decoded_message.lower().startswith(command):
                        handle_command(commands[command], place_id, server_id)

        # Prepare the Discord payload
        discord_payload = {
            "embeds": [
                {
                    "title": "Server Chat Log",
                    "description": "Server Activity Report",
                    "color": 16776960,
                    "fields": [
                        {"name": "Place ID", "value": str(place_id), "inline": True},
                        {"name": "Server ID", "value": str(server_id), "inline": True},
                        {"name": "Private Server URL", "value": private_server_url, "inline": False},
                        {"name": "Players Online", "value": "\n".join([f"{name} ({display_name})" for name, display_name in player_data.items()]), "inline": False},
                        {"name": "Join Logs", "value": "\n".join(join_logs[-10:]) if join_logs else "No recent joins.", "inline": False},
                        {"name": "Leave Logs", "value": "\n".join(leave_logs[-10:]) if leave_logs else "No recent leaves.", "inline": False},
                    ],
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }

        # Add chat logs as separate embeds
        for chat_entry in new_chat_logs:
            discord_payload["embeds"].append({
                "description": chat_entry["content"],
                "timestamp": chat_entry["timestamp"]
            })

            if len(discord_payload["embeds"]) >= 10:
                send_to_discord(discord_payload)
                discord_payload["embeds"] = []

        # Send any remaining embeds
        if discord_payload["embeds"]:
            send_to_discord(discord_payload)

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print("Error while processing request:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

def send_to_discord(payload):
    """Send data to Discord webhook."""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.post(discord_webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error while sending to Discord: {e}")

def reset_sent_messages():
    """Reset the sent messages list periodically."""
    global sent_messages
    sent_messages.clear()

# Reset sent messages every 60 seconds
Timer(60, reset_sent_messages).start()

if __name__ == "__main__":
    app.run(debug=True)
