from flask import Flask, request, jsonify

app = Flask(__name__)
LOG_FILE = "logs.txt"
# Limit request size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

@app.route('/log', methods=['POST'])
def log_message():
    """
    Log a message to the server.
    Expects JSON: {"message": "your message"}
    """
    # Ensure request is JSON
    data = request.get_json(silent=True)
    
    if data is None or not isinstance(data, dict) or 'message' not in data:
        return jsonify({"error": "Invalid request, 'message' field is required"}), 400
    
    message = data['message']
    
    # Validate that message is a string to prevent type-confusion
    if not isinstance(message, str):
        return jsonify({"error": "Message must be a string"}), 400

    # Security: Prevent Log Injection (CRLF injection)
    # We strip carriage returns and line feeds to ensure one log entry per line
    sanitized_message = message.replace('\r', '').replace('\n', '')
    
    try:
        # Using a hardcoded filename prevents path traversal
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
        return "", 200
    except Exception:
        # Generic error to avoid leaking internal system details/stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve all logged messages.
    Returns a plain text response.
    """
    try:
        # Using a hardcoded filename prevents path traversal
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.read()
        return logs, 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        # If file doesn't exist yet, return empty string as per spec
        return "", 200, {'Content-Type': 'text/plain'}
    except Exception:
        # Generic error to avoid leaking internal system details
        return "Internal server error", 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)