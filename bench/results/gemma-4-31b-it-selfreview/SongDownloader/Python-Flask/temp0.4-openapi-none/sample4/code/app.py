import os
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = os.path.abspath("/var/songs")

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that file's content.
    """
    # Resource exhaustion: Bound request size to prevent memory exhaustion from huge JSON payloads
    # Flask's default is usually sufficient, but we explicitly check for JSON validity
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict) or 'filename' not in data:
        return jsonify({"error": "Invalid input"}), 400

    filename = data['filename']

    # Validate that filename is a string to prevent type-confusion attacks
    if not isinstance(filename, str):
        return jsonify({"error": "Invalid input"}), 400

    # Path Traversal Prevention:
    # 1. Reject absolute paths and directory traversal sequences ('..')
    if os.path.isabs(filename) or '..' in filename:
        return jsonify({"error": "Invalid input"}), 400

    # 2. Use os.path.basename to ensure we only take the filename part
    # 3. Join with the absolute base directory
    safe_filename = os.path.basename(filename)
    if not safe_filename:
        return jsonify({"error": "Invalid input"}), 400
        
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # 4. Final verification: Resolve the real path and ensure it is still within SONGS_DIRECTORY
    # This prevents bypasses using symlinks or platform-specific quirks
    try:
        # We check existence first to avoid errors in realpath on some OSs
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return jsonify({"error": "File does not exist"}), 404
        
        # Resolve the absolute path to eliminate any remaining symbolic links or relative segments
        resolved_path = os.path.realpath(file_path)
        if not resolved_path.startswith(SONGS_DIRECTORY):
            return jsonify({"error": "Invalid input"}), 400
            
    except Exception:
        # Generic error handling to avoid leaking internal system details/stack traces
        return jsonify({"error": "Internal server error"}), 500

    try:
        # send_file handles the streaming of the file content efficiently.
        # mimetype is hardcoded to audio/mpeg as per OpenAPI spec.
        return send_file(
            resolved_path,
            mimetype='audio/mpeg',
            as_attachment=False
        )
    except Exception:
        # Catch-all for I/O errors to prevent leaking stack traces
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Ensure the directory exists for the sake of the server starting
    if not os.path.exists(SONGS_DIRECTORY):
        try:
            os.makedirs(SONGS_DIRECTORY, exist_ok=True)
        except Exception:
            pass

    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)