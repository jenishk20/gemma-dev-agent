from flask import Flask, request, jsonify
import os

app = Flask(__name__)

LOG_FILE = "logs.txt"

@app.route('/log', methods=['POST'])
def log_message():
    """
    Log a message to the server.
    Expects JSON body: {"message": "string"}
    """
    data = request.get_json()
    
    # Validate that the request body is JSON and contains the 'message' key
    if not data or 'message' not in data:
        return jsonify({"error": "Invalid request. Please provide a JSON body with a 'message' field."}), 400
    
    message = data['message']
    
    # Validate that the message is a string to prevent unexpected data types
    if not isinstance(message, str):
        return jsonify({"error": "Message must be a string."}), 400

    try:
        # Append the message to the file. 
        # We strip any existing newlines from the message to ensure one log per line.
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message.replace('\n', ' ') + "\n")
        
        return jsonify({"status": "Log message successful"}), 200
    except Exception as e:
        return jsonify({"error": "Internal server error writing to log file."}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Retrieve all logged messages.
    Returns a plain text response.
    """
    try:
        if not os.path.exists(LOG_FILE):
            return "", 200
            
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            
        return content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return "Internal server error reading logs.", 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)