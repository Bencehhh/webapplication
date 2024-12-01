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

    try:
        data = request.json  # Parse JSON from incoming request
        print("Received data:", json.dumps(data, indent=4))  # Debugging: print received data

        # Extract information
        place_id = data.get('placeId', 'N/A')
        server_id = data.get('serverId', 'N/A')
        player_data = data.get('playerData', "No players in the server.")
        join_leave_logs = data.get('joinLeaveLogs', "No recent activity.")
        chat_logs = data.get('chatLogs', "No messages.")
        
        # Construct Discord payload
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

        # Print the Discord payload for debugging
        print("Sending payload to Discord:", json.dumps(discord_payload, indent=4))

        # Send data to Discord webhook
        headers = {}
        response = requests.post(discord_webhook_url, json=discord_payload, headers=headers)

        # Check Discord response
        print("Discord Response:", response.status_code, response.text)
        if response.status_code == 204:
            print("Successfully forwarded data to Discord!")
        else:
            print(f"Failed to forward data to Discord. Status: {response.status_code}, Response: {response.text}")
            return jsonify({"status": "error", "message": "Failed to forward data to Discord"}), 500
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("Error while processing request:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Let the platform handle the port (no explicit mention of port)
    app.run(debug=True, host='0.0.0.0')