import json
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import re

app = Flask("__main__")

discord_webhook_url = os.getenv("WEBHOOK_URL")
api_key = os.getenv("API_KEY")

MAX_CHAT_LOGS = 50
chat_buffer = []

def decode_message(message):
    """Decode a message by replacing sequences of '#' with '[REDACTED]'."""
    # Use regex to replace sequences of one or more '#' characters with '[REDACTED]'
    return re.sub(r'#+', '[REDACTED]', message)

def add_to_chat_buffer(chat_log):
    """Add a chat log to the rolling buffer, maintaining size limit."""
    global chat_buffer
    chat_buffer.append(chat_log)
    if len(chat_buffer) > MAX_CHAT_LOGS:
        chat_buffer.pop(0)  # Remove the oldest message

def send_to_discord(payload):
    """Send data to Discord webhook."""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        # Debugging: print the payload to ensure it is correct
        print("Payload to send to Discord:", json.dumps(payload, indent=4))
        
        response = requests.post(discord_webhook_url, json=payload, headers=headers, timeout=10)
        print(f"Discord HTTP Status: {response.status_code}")
        print(f"Discord Response: {response.text}")
        response.raise_for_status()
        return response.status_code == 204
    except requests.exceptions.RequestException as e:
        print(f"Error while sending to Discord: {str(e)}")
        return False

@app.route('/', methods=['POST'])
def root():
    try:
        data = request.json

        # Extract the data from the incoming payload
        place_id = data.get('placeId', 'N/A')
        server_id = data.get('serverId', 'N/A')
        private_server_id = data.get('privateServerId', 'N/A')
        private_server_url = f"https://www.roblox.com/games/{place_id}?privateServerLinkCode={private_server_id}" if private_server_id != 'N/A' else 'N/A'

        # Process chat logs (decode them before adding to the buffer)
        chat_logs = data.get('chatLogs', [])
        for chat_log in chat_logs:
            timestamp = datetime.utcnow().isoformat() + "Z"
            decoded_message = decode_message(chat_log)  # Decode the chat message
            add_to_chat_buffer({
                "content": decoded_message,
                "timestamp": timestamp
            })

        # Prepare the Discord payload with the necessary data
        discord_payload = {
            "embeds": [
                {
                    "title": "Moderation Log",
                    "description": "Server Activity Report",
                    "color": 3447003,
                    "fields": [
                        {"name": "Place ID", "value": str(place_id), "inline": True},
                        {"name": "Server ID", "value": str(server_id), "inline": True},
                        {"name": "Private Server URL", "value": private_server_url, "inline": False}
                    ],
                    "thumbnail": {"url": ""},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }

        # Add the chat logs as separate embeds
        for chat_entry in chat_buffer:
            discord_payload["embeds"].append({
                "description": chat_entry["content"],
                "timestamp": chat_entry["timestamp"]
            })

            # If we reach 10 embeds, send the current batch to Discord
            if len(discord_payload["embeds"]) >= 10:
                send_to_discord(discord_payload)
                discord_payload["embeds"] = []  # Reset embeds after sending

        # Send any remaining embeds
        if discord_payload["embeds"]:
            send_to_discord(discord_payload)

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print("Error while processing request:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
