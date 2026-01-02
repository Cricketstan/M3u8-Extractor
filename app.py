#!/usr/bin/env python3
# app.py - Simple Flask app with health check

import os
import json
import subprocess
import threading
from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# Simple health check endpoint
@app.route('/')
def health():
    return jsonify({
        "status": "running",
        "service": "stream-capture",
        "timestamp": time.time()
    })

@app.route('/capture', methods=['POST', 'GET'])
def capture():
    """Run the capture script"""
    if request.method == 'GET':
        # Get URL from query parameter
        url = request.args.get('url', os.getenv('TARGET_URL', 'https://news.abplive.com/live-tv'))
    else:
        # Get URL from JSON body
        data = request.get_json() or {}
        url = data.get('url', os.getenv('TARGET_URL', 'https://news.abplive.com/live-tv'))
    
    try:
        # Run the capture script as a subprocess
        result = subprocess.run(
            ['python', 'fetch_stream_optimized.py', url],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        if result.returncode == 0:
            # Parse output to extract URLs
            lines = result.stdout.strip().split('\n')
            urls = [line for line in lines if line.startswith('http') and '.m3u8' in line]
            
            return jsonify({
                "success": True,
                "url": url,
                "streams_found": len(urls),
                "streams": urls,
                "output": result.stdout[-1000:]  # Last 1000 chars
            })
        else:
            return jsonify({
                "success": False,
                "url": url,
                "error": f"Script failed with code {result.returncode}",
                "stdout": result.stdout[-1000:],
                "stderr": result.stderr[-1000:]
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Script timed out after 45 seconds"
        }), 408
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
