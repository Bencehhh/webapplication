active_players = {}  # Tracks currently active players and their join times

@app.route('/', methods=['POST'])
def root():
    try:
        data = request.json

        # Extract server and place information
        place_id = data.get('placeId', 'N/A')
        server_id = data.get('serverId', 'N/A')
        private_server_id = data.get('privateServerId', 'N/A')
        private_server_url = f"https://www.roblox.com/games/{place_id}?privateServerLinkCode={private_server_id}" if private_server_id != 'N/A' else 'N/A'

        # Update player data
        player_list = data.get('playerData', '').split('\n')
        global player_data, join_logs, leave_logs

        # Reset player data and process player list
        player_data.clear()
        for player_info in player_list:
            name, display_name = player_info.split(" (")
            display_name = display_name.rstrip(")")
            player_data[name] = display_name

        # Process join and leave logs
        join_leave_logs = data.get('joinLeaveLogs', '').split('\n')
        for log in join_leave_logs:
            if "joined the game" in log:
                # Extract player name and display name from log
                match = re.match(r"(.+) \((.+)\) joined the game\.", log)
                if match:
                    name, display_name = match.groups()
                    if name not in active_players:
                        # Add to active players and log their join
                        timestamp = datetime.utcnow().isoformat() + "Z"
                        active_players[name] = timestamp
                        join_logs.append(f"{log} at {timestamp}")
            elif "left the game" in log:
                # Extract player name and display name from log
                match = re.match(r"(.+) \((.+)\) left the game\.", log)
                if match:
                    name, _ = match.groups()
                    if name in active_players:
                        # Remove from active players and log their leave
                        timestamp = datetime.utcnow().isoformat() + "Z"
                        del active_players[name]
                        leave_logs.append(f"{log} at {timestamp}")

        # Process chat logs (decode them before adding to the buffer)
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

        # Prepare the Discord payload
        discord_payload = {
            "embeds": [
                {
                    "title": "Moderation Log",
                    "description": "Server Activity Report",
                    "color": 3447003,
                    "fields": [
                        {"name": "Place ID", "value": str(place_id), "inline": True},
                        {"name": "Server ID", "value": str(server_id), "inline": True},
                        {"name": "Private Server ID", "value": str(private_server_id), "inline": True},
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

            # Send in batches of 10 embeds to avoid Discord limits
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
