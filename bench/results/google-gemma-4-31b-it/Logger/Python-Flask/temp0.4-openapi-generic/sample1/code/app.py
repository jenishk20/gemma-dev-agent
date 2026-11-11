from flask import Flask, request, jsonify

app = Flask(__name__)

LOG_FILE = "logs.txt"

@app.route('/log', methods=['POST'])
def log_message():
    """
    Log a message to the server.
    Expects JSON body: {"message": "your message"}
    """
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' in request body"}), 400
    
    message = data['message']
    
    # Basic validation to ensure the message is a string
    if not isinstance(message, str):
        return jsonify({"error": "Message must be a string"}), 400

    try:
        # We strip any trailing newlines to prevent log injection (splitting one log into multiple lines)
        # and ensure each log entry is exactly one line.
        sanitized_message = message.replace('\n', ' ').replace('\r', ' ')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
        return jsonify({"status": "Log message successful"}), 200
    except Exception as e:
        return jsonify({"error": "Internal server error writing to log"}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve all logged messages.
    Returns the content of logs.txt as plain text.
    """
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        # If the file hasn't been created yet, return an empty string
        return "", 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return "Internal server error reading logs", 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)