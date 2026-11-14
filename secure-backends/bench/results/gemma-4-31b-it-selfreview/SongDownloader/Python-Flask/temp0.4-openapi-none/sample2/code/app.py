import os
from flask import Flask, request, send_from_directory, jsonify

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = os.path.abspath("/var/songs")

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Expects a JSON body with a 'filename' property.
    """
    # Resource exhaustion: Bound request size to prevent large JSON payloads
    # Flask's default is usually reasonable, but we ensure we handle it.
    if request.content_length and request.content_length > 1024 * 10: # 10KB limit for the JSON request
        return jsonify({"error": "Request body too large"}), 400

    # Validate that the request is JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input"}), 400

    # Validate that filename is provided and is a string
    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input"}), 400

    # Path Traversal Prevention:
    # 1. Reject absolute paths and directory traversal sequences (..)
    if os.path.isabs(filename) or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({"error": "Invalid input"}), 400

    # 2. Resolve the final path and verify it is strictly within the SONGS_DIRECTORY
    try:
        # Join and normalize the path
        target_path = os.path.abspath(os.path.join(SONGS_DIRECTORY, filename))
        
        # Ensure the resolved path starts with the base directory path
        if not target_path.startswith(SONGS_DIRECTORY + os.sep) and target_path != SONGS_DIRECTORY:
            return jsonify({"error": "Invalid input"}), 400
            
        # Check if the file exists and is actually a file (not a directory)
        if not os.path.isfile(target_path):
            return jsonify({"error": "File does not exist"}), 404

    except Exception:
        # Generic error to avoid leaking internal system details/stack traces
        return jsonify({"error": "Invalid input"}), 400

    # Stream the file from the directory
    try:
        # send_from_directory provides additional security layers against traversal
        return send_from_directory(
            directory=SONGS_DIRECTORY, 
            path=filename, 
            mimetype='audio/mpeg'
        )
    except Exception:
        # Return documented error status code without leaking internal details
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)