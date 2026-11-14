from flask import Flask, request, jsonify, Response
import os

app = Flask(__name__)

LOG_FILE = "logs.txt"

@app.route('/log', methods=['POST'])
def log_message():
    """
    Log a message to the server.
    Expects JSON body: {"message": "your message"}
    """
    data = request.get_json(silent=True)
    
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    
    message = data.get('message')
    
    if message is None or not isinstance(message, str):
        return jsonify({"error": "Missing or invalid 'message' field"}), 400

    # Sanitize input: remove newlines to ensure one log per line as per requirements
    # and prevent log injection.
    sanitized_message = message.replace('\n', ' ').replace('\r', ' ')

    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(sanitized_message + '\n')
    except Exception as e:
        return jsonify({"error": "Internal server error writing to log"}), 500

    return Response(status=200)

@app.route('/logs', methods=['GET'])
def retrieve_logs():
    """
    Retrieve all logged messages.
    Returns content as text/plain.
    """
    try:
        if not os.path.exists(LOG_FILE):
            return Response("", mimetype='text/plain')
            
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return Response(content, mimetype='text/plain')
    except Exception as e:
        return Response("Internal server error reading logs", status=500, mimetype='text/plain')

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)