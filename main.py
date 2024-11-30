from flask import Flask, jsonify, request
import os

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")


@app.route('/')
def home():
    return "Welcome and thank you for using our system!"


@app.route('/get-webhook', methods=['GET'])
def get_webhook():

    api_key = request.args.get('api_key')

    if api_key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify({"webhook_url": WEBHOOK_URL})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
