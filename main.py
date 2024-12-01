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
    if not discord_webhook_url or not api_key:
        return jsonify({"status": "error", "message": "Missing URL or API key"}), 400

    data = request.json  # Parse JSON from incoming request
    
    # Debugging: Print the received data
    print("Received data:", json.dumps(data, indent=4))
    
    # Extract information
    place_id = data.get('placeId', 'N/A')
    server_id = data.get('serverId', 'N/A')
    player_data = data.get('playerData', "No players in the server.")
    join_leave_logs = data.get('joinLeaveLogs', "No recent activity.")
    chat_logs = data.get('chatLogs', "No messages.")
    
    discord_payload = {
        "embeds": [{
            "title": "Moderation Log",
            "description": "Server Activity Report",
            "color": 3447003,
            "fields": [
                {"name": "Place ID", "value": str(place_id), "inline": True},
                {"name": "Server ID", "value": str(server_id), "inline": True},
                {"name": "Players", "value": player_data, "inline": False},
                {"name": "Join/Leave Logs", "value": join_leave_logs, "inline": False},
                {"name": "Chat Logs", "value": chat_logs, "inline": False}
            ]
        }]
    }

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.post(discord_webhook_url, json=discord_payload, headers=headers)
        print("Discord Response:", response.status_code, response.text)  # Debug
        if response.status_code == 204:
            print("Successfully forwarded data to database!")
        else:
            print("Failed to forward data to database!:", response.status_code, response.text)
    except Exception as e:
        print("Error while sending to database:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True)
