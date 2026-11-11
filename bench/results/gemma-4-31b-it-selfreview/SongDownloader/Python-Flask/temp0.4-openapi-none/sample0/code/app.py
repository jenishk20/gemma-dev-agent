import os
from flask import Flask, request, send_from_directory, jsonify

app = Flask(__name__)

# The directory where songs are stored as per requirements
SONGS_DIRECTORY = '/var/songs'

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Expects a JSON body with a 'filename' key.
    """
    # Resource exhaustion: Limit request body size to prevent memory exhaustion
    # Flask's default is usually sufficient, but we ensure we handle JSON safely.
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid input"}), 400

    if data is None:
        return jsonify({"error": "Invalid input"}), 400

    # Extract filename from the request body
    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input"}), 400

    try:
        # PATH TRAVERSAL PROTECTION:
        # 1. Use os.path.basename to strip any directory components provided by the user.
        # 2. Verify the resulting filename is not empty and not just '.' or '..'.
        safe_filename = os.path.basename(filename)
        
        if not safe_filename or safe_filename in ('.', '..'):
            return jsonify({"error": "Invalid input"}), 400

        # 3. Resolve the absolute path and verify it is actually within the SONGS_DIRECTORY.
        # This prevents bypasses involving symlinks or complex pathing.
        base_path = os.path.abspath(SONGS_DIRECTORY)
        target_path = os.path.abspath(os.path.join(base_path, safe_filename))

        if not target_path.startswith(base_path):
            return jsonify({"error": "Invalid input"}), 400

        # Check if file exists and is a file (not a directory)
        if not os.path.isfile(target_path):
            return jsonify({"error": "File does not exist"}), 404

        # Stream the file from the directory. 
        # send_from_directory provides additional security layers.
        return send_from_directory(
            SONGS_DIRECTORY, 
            safe_filename, 
            mimetype='audio/mpeg'
        )

    except Exception:
        # Error handling: Catch all exceptions to prevent leaking stack traces 
        # or internal server details to the client.
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)