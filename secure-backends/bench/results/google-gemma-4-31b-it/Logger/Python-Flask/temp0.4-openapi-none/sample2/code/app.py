from flask import Flask, request, jsonify

app = Flask(__name__)
LOG_FILE = "logs.txt"

@app.route('/log', methods=['POST'])
def log_message():
    """
    Log a message to the server.
    Expects JSON: {"message": "your message"}
    """
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' in request body"}), 400
    
    message = data['message']
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
        return jsonify({"status": "Log message successful"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve all logged messages.
    Returns a plain text response.
    """
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.read()
        return logs, 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        # If file doesn't exist yet, return empty string
        return "", 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return str(e), 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)