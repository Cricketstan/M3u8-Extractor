from flask import Flask, jsonify
import json, os

app = Flask(__name__)

@app.route("/m3u8.json")
def m3u8():
    if not os.path.exists("m3u8.json"):
        return jsonify({"status": "waiting"}), 404
    with open("m3u8.json") as f:
        return jsonify(json.load(f))

@app.route("/")
def home():
    return "M3U8 Extractor Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
