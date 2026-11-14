import os
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = "/var/songs"

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Expects a JSON body with a 'filename' key.
    """
    # Resource Exhaustion: Limit request body size to prevent memory exhaustion
    # Flask's default is usually sufficient, but we ensure we handle JSON safely.
    if request.content_length and request.content_length > 10 * 1024: # 10KB limit for JSON request
        return jsonify({"error": "Request body too large"}), 400

    # Untrusted input reaching a file path: Validate JSON input
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input, expected JSON"}), 400

    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input, 'filename' is required and must be a string"}), 400

    # Path Traversal Prevention:
    # 1. Reject absolute paths and directory traversal sequences explicitly.
    if os.path.isabs(filename) or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({"error": "Invalid input"}), 400

    # 2. Use os.path.basename as a secondary layer of defense.
    safe_filename = os.path.basename(filename)
    if not safe_filename:
        return jsonify({"error": "Invalid input"}), 400

    # 3. Resolve the absolute path and verify it resides within the target directory.
    # This prevents symlink attacks or clever path manipulations.
    base_path = os.path.abspath(SONGS_DIRECTORY)
    file_path = os.path.abspath(os.path.join(base_path, safe_filename))

    if not file_path.startswith(base_path):
        return jsonify({"error": "Invalid input"}), 400

    # Error Handling: Check if file exists and is a file (not a directory)
    # We use a generic 404 as per OpenAPI spec.
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return jsonify({"error": "File does not exist"}), 404

    try:
        # send_file handles the streaming of the file content efficiently.
        # mimetype is set to audio/mpeg as per OpenAPI spec.
        return send_file(
            file_path, 
            mimetype='audio/mpeg', 
            as_attachment=False
        )
    except Exception:
        # Error handling: Catch all exceptions to prevent leaking stack traces.
        # Return a generic 500 or 400 depending on the nature of the failure.
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Ensure the directory exists for the sake of the demo.
    if not os.path.exists(SONGS_DIRECTORY):
        try:
            os.makedirs(SONGS_DIRECTORY, mode=0o755)
        except PermissionError:
            pass

    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)