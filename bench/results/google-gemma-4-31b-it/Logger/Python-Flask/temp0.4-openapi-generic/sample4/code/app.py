from flask import Flask, request, jsonify, Response

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
        return jsonify({"error": "Invalid request body. 'message' field is required."}), 400
    
    message = data['message']
    
    # Validate that the message is a string to prevent unexpected types
    if not isinstance(message, str):
        return jsonify({"error": "Message must be a string."}), 400

    # Sanitize input: remove newlines to ensure one log per line as per requirements
    # and prevent log injection attacks.
    sanitized_message = message.replace('\n', ' ').replace('\r', ' ')

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
    except IOError as e:
        return jsonify({"error": "Internal server error writing to log file."}), 500

    return jsonify({"status": "Log message successful"}), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve all logged messages.
    Returns the content of logs.txt as plain text.
    """
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content, mimetype='text/plain')
    except FileNotFoundError:
        # Return empty string if file hasn't been created yet
        return Response("", mimetype='text/plain')
    except IOError as e:
        return jsonify({"error": "Internal server error reading log file."}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)