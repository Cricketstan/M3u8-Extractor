#!/usr/bin/env python3
# app.py - Simple Flask app with health check

import os
import json
import subprocess
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
        # Set environment variables for the subprocess
        env = os.environ.copy()
        env['TARGET_URL'] = url
        env['MAX_WAIT_SECONDS'] = os.getenv('MAX_WAIT_SECONDS', '20')
        env['STARTUP_TIMEOUT'] = os.getenv('STARTUP_TIMEOUT', '30')
        
        # Run the capture script directly (not as subprocess)
        # Import and run the module
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import and run main function
        import fetch_stream_optimized
        import io
        import contextlib
        
        # Capture output
        output_capture = io.StringIO()
        with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(output_capture):
            # Run the main function
            try:
                # Since fetch_stream_optimized.main() calls sys.exit(), we need to catch it
                old_sys_exit = sys.exit
                def mock_exit(code=0):
                    raise SystemExit(code)
                sys.exit = mock_exit
                
                fetch_stream_optimized.main()
                return_code = 0
            except SystemExit as e:
                return_code = e.code if isinstance(e.code, int) else 0
            finally:
                sys.exit = old_sys_exit
        
        output = output_capture.getvalue()
        
        # Parse output to extract URLs
        urls = []
        for line in output.split('\n'):
            if 'http' in line and '.m3u8' in line:
                # Clean the line (remove timestamps and colors)
                clean_line = line.strip()
                # Remove color codes if present
                import re
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', clean_line)
                # Remove timestamps
                clean_line = re.sub(r'^\d{2}:\d{2}:\d{2}\s+', '', clean_line)
                if clean_line.startswith('http'):
                    urls.append(clean_line)
        
        if return_code == 0 and urls:
            return jsonify({
                "success": True,
                "url": url,
                "streams_found": len(urls),
                "streams": urls,
                "output": output[-2000:]  # Last 2000 chars
            })
        else:
            return jsonify({
                "success": False,
                "url": url,
                "error": f"No streams found or script returned code {return_code}",
                "output": output[-2000:],
                "return_code": return_code
            }), 500 if return_code != 0 else 404
            
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
