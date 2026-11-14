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
    # Ensure request is JSON
    data = request.get_json(silent=True)
    
    if data is None or not isinstance(data, dict) or 'message' not in data:
        # Return 400 for malformed input as per standard API error handling
        return jsonify({"error": "Invalid request body"}), 400
    
    message = data['message']
    
    # Ensure message is a string to avoid type errors
    if not isinstance(message, str):
        return jsonify({"error": "Message must be a string"}), 400

    # SECURITY: Prevent Log Injection (CRLF injection)
    # Strip carriage return and line feed characters to ensure one log entry per line
    sanitized_message = message.replace('\r', '').replace('\n', '')
    
    try:
        # The filename is hardcoded as "logs.txt", preventing path traversal
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
        return jsonify({"status": "Log message successful"}), 200
    except Exception:
        # SECURITY: Generic error message to avoid leaking internal system details/stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve all logged messages.
    Returns a plain text response.
    """
    try:
        # The filename is hardcoded, preventing path traversal
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.read()
        return logs, 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        # If the file doesn't exist yet, return an empty string as per spec
        return "", 200, {'Content-Type': 'text/plain'}
    except Exception:
        # SECURITY: Generic error message to avoid leaking internal system details
        return "Internal server error", 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)