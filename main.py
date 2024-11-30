from flask import Flask, jsonify, request
import os
import json
import requests

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

@app.route('/')
def home():
    return "Welcome to the Moderation Logger Web App!"

@app.route('/get-webhook', methods=['GET'])
def get_webhook():
    api_key = request.args.get('api_key')

    if api_key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify({"webhook_url": WEBHOOK_URL})

@app.route('/webhook', methods=['POST'])
def webhook():
    if not API_KEY or not WEBHOOK_URL:
        return jsonify({"status": "error", "message": "Server misconfiguration"}), 500

    # Parse incoming request
    data = request.json
    if not data:
        print("Error: No data received.")
        return jsonify({"status": "error", "message": "No data received"}), 400

    # Debugging: Log incoming data
    print("Received data:", json.dumps(data, indent=4))

    # Extract data for Discord
    place_id = data.get("placeId")
    server_id = data.get("serverId")
    player_data = data.get("playerData")
    join_leave_logs = data.get("joinLeaveLogs")
    chat_logs = data.get("chatLogs")
    private_server_links = data.get("privateServerLinks")

    # Ensure critical fields exist
    if not place_id or not server_id:
        print("Error: Missing critical fields (placeId or serverId).")
        return jsonify({"status": "error", "message": "Missing critical fields"}), 400

    # Prepare Discord payload
    discord_payload = {
        "embeds": [{
            "title": "Moderation Log",
            "description": "Server Activity Report",
            "color": 3447003,
            "fields": [
                {"name": "Place ID", "value": place_id, "inline": True},
                {"name": "Server ID", "value": server_id, "inline": True},
                {"name": "Players", "value": player_data or "No players", "inline": False},
                {"name": "Join/Leave Logs", "value": join_leave_logs or "No recent activity", "inline": False},
                {"name": "Chat Logs", "value": chat_logs or "No messages", "inline": False},
                {"name": "Private Server Links", "value": private_server_links or "No links shared", "inline": False}
            ]
        }]
    }

    # Send to Discord
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.post(WEBHOOK_URL, json=discord_payload, headers=headers)

    if response.status_code == 204:
        print("Successfully sent data to Discord.")
        return jsonify({"status": "success"}), 200
    else:
        print("Failed to send to Discord:", response.text)
        return jsonify({"status": "error", "message": "Failed to send to Discord"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
