from flask import Flask, request, jsonify, Response
import os

app = Flask(__name__)

LOG_FILE = "logs.txt"

def write_log(message):
    """Appends a message to the log file, ensuring it is a single line."""
    # Sanitize message to remove newlines to prevent log injection
    sanitized_message = message.replace('\n', ' ').replace('\r', ' ')
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(sanitized_message + "\n")

def read_logs():
    """Reads all logs from the file."""
    if not os.path.exists(LOG_FILE):
        return ""
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()

@app.route('/log', methods=['POST'])
def log_message():
    """
    Endpoint to log a message.
    Expects JSON body: {"message": "text"}
    """
    data = request.get_json(silent=True)
    
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    
    message = data.get('message')
    if message is None or not isinstance(message, str):
        return jsonify({"error": "Missing or invalid 'message' field"}), 400

    write_log(message)
    return jsonify({"status": "Log message successful"}), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Endpoint to retrieve all logs.
    Returns plain text.
    """
    logs_content = read_logs()
    return Response(logs_content, mimetype='text/plain')

if __name__ == '__main__':
    # Ensure log file exists
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'a').close()
        
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)