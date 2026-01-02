from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "m3u8 StreamSniper running"

@app.route("/extract")
def extract():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "url parameter missing"}), 400

    env = os.environ.copy()
    env["TARGET_URL"] = url
    env["MAX_WAIT_SECONDS"] = "20"

    result = subprocess.run(
        ["python", "fetch_stream.py"],
        capture_output=True,
        text=True,
        env=env
    )

    return jsonify({
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
