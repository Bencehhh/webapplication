import json
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Retrieve the secret keys from environment variables
discord_webhook_url = os.getenv("WEBHOOK_URL")
api_key = os.getenv("API_KEY")

@app.route('/webhook', methods=['POST'])
def webhook():
    # Ensure that the webhook URL and API key are available
    if not discord_webhook_url or not api_key:
        return jsonify({"status": "error", "message": "Missing webhook URL or API key"}), 400
    
    data = request.json  # Parse JSON from incoming request
    
    # Debugging: Print the received data
    print("Received data:", json.dumps(data, indent=4))
    
    # Extract information from the payload
    place_id = data.get('placeId')
    server_id = data.get('serverId')
    player_data = data.get('playerData')
    join_leave_logs = data.get('joinLeaveLogs')
    chat_logs = data.get('chatLogs')
    
    # Prepare the Discord webhook payload
    discord_payload = {
        "embeds": [{
            "title": "Moderation Log",
            "description": "Server Activity Report",
            "color": 3447003,  # Blue color
            "fields": [
                {"name": "Place ID", "value": str(place_id), "inline": True},
                {"name": "Server ID", "value": str(server_id), "inline": True},
                {"name": "Players", "value": player_data if player_data else "No players in the server.", "inline": False},
                {"name": "Join/Leave Logs", "value": join_leave_logs if join_leave_logs else "No recent activity.", "inline": False},
                {"name": "Chat Logs", "value": chat_logs if chat_logs else "No messages.", "inline": False}
            ],
            "footer": {
                "text": "Moderation Logs",
                "icon_url": "https://i.imgur.com/AfFp7pu.png"  # Optional footer icon
            },
            "timestamp": "2024-11-30T00:00:00Z"  # Use the current UTC time here
        }]
    }

    # Send data to Discord webhook with the API key as a header (if necessary)
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(discord_webhook_url, json=discord_payload, headers=headers)

    if response.status_code == 204:
        print("Successfully forwarded data to Discord!")
    else:
        print("Failed to forward data to Discord:", response.text)

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True)
