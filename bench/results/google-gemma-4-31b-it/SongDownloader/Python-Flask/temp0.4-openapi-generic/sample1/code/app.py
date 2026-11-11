import os
from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = "/var/songs"

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Expects a JSON body with a 'filename' key.
    """
    # Validate that the request is JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input: Request body must be JSON"}), 400

    # Extract filename from request body
    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input: 'filename' is required and must be a string"}), 400

    # SECURITY: Prevent Path Traversal attacks.
    # secure_filename removes directory separators and null bytes.
    safe_filename = secure_filename(filename)
    
    if not safe_filename:
        return jsonify({"error": "Invalid filename provided"}), 400

    # Check if the file exists in the target directory
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return jsonify({"error": "File does not exist"}), 404

    # Stream the file back to the user.
    # send_from_directory is preferred as it provides additional security checks
    # and handles range requests for streaming audio.
    return send_from_directory(
        directory=SONGS_DIRECTORY, 
        path=safe_filename, 
        mimetype='audio/mpeg'
    )

if __name__ == '__main__':
    # Ensure the directory exists to prevent crash on startup, 
    # though in production this would be managed by the environment.
    if not os.path.exists(SONGS_DIRECTORY):
        os.makedirs(SONGS_DIRECTORY, exist_ok=True)
        
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)