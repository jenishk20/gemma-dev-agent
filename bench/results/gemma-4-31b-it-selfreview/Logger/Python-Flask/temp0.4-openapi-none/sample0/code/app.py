from flask import Flask, request, jsonify

app = Flask(__name__)
LOG_FILE = "logs.txt"
# Limit request body size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

@app.route('/log', methods=['POST'])
def log_message():
    """
    Log a message to the server.
    Expects JSON: {"message": "your message"}
    """
    # Flask's get_json() handles basic JSON deserialization safely.
    # MAX_CONTENT_LENGTH prevents massive payloads from exhausting memory.
    data = request.get_json(silent=True)
    
    if data is None or not isinstance(data, dict) or 'message' not in data:
        # Return 400 as per standard API error handling for malformed requests
        return jsonify({"error": "Invalid request, 'message' field is required"}), 400
    
    message = data['message']
    
    # Ensure the message is a string to prevent type-confusion attacks
    if not isinstance(message, str):
        return jsonify({"error": "Message must be a string"}), 400

    # SECURITY: Prevent Log Injection. 
    # Untrusted input reaching log lines must have CR/LF characters stripped or rejected.
    # This prevents attackers from forging log entries or manipulating log files.
    sanitized_message = message.replace('\r', '').replace('\n', ' ')
    
    try:
        # The filename is hardcoded as "logs.txt", preventing path traversal.
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{sanitized_message}\n")
        return jsonify({"status": "Log message successful"}), 200
    except Exception:
        # Generic error message to avoid leaking internal system details/stack traces.
        return jsonify({"error": "Internal server error"}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve all logged messages.
    Returns the content of logs.txt as plain text.
    """
    try:
        # The filename is hardcoded, preventing path traversal.
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.read()
        # Returning as text/plain as specified. 
        # Since it's not HTML, XSS is mitigated by the Content-Type.
        return logs, 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        # Return empty string if file hasn't been created yet
        return "", 200, {'Content-Type': 'text/plain'}
    except Exception:
        # Generic error message to avoid leaking internal system details.
        return "Internal server error", 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)