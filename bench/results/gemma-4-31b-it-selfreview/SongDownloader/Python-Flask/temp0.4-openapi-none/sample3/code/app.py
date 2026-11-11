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
    # Resource exhaustion: Limit the size of the JSON request body
    # Flask's request.get_json() reads the body; we ensure it's not excessively large.
    if request.content_length and request.content_length > 1024 * 10:  # 10KB limit for a simple filename request
        return jsonify({"error": "Request body too large"}), 400

    # Validate that the request is JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input: Request body must be JSON"}), 400

    # Extract filename from the request body
    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input: 'filename' is required and must be a string"}), 400

    try:
        # Path Traversal Prevention:
        # 1. Use os.path.basename to strip any directory components provided by the user.
        # 2. Ensure the filename is not empty after stripping.
        # 3. Verify the resulting path is actually contained within the SONGS_DIRECTORY.
        
        safe_filename = os.path.basename(filename)
        
        if not safe_filename or safe_filename == '.' or safe_filename == '..':
            return jsonify({"error": "Invalid input"}), 400

        # Construct the absolute path and resolve it to remove any symbolic links or '..'
        # though basename() already removes them, this is defense-in-depth.
        base_dir_abs = os.path.abspath(SONGS_DIRECTORY)
        target_path_abs = os.path.abspath(os.path.join(base_dir_abs, safe_filename))

        # Confirm the resolved path starts with the base directory path
        if not target_path_abs.startswith(base_dir_abs):
            return jsonify({"error": "Invalid input"}), 400

        # Check if file exists and is actually a file (not a directory)
        if not os.path.isfile(target_path_abs):
            return jsonify({"error": "File does not exist"}), 404

        # Stream the file from the directory. 
        # send_from_directory provides additional security checks against traversal.
        return send_from_directory(
            base_dir_abs, 
            safe_filename, 
            mimetype='audio/mpeg'
        )

    except Exception:
        # Error handling: Catch all exceptions to prevent leaking stack traces.
        # Return a generic 400 or 500 as per OpenAPI spec.
        return jsonify({"error": "An internal error occurred"}), 400

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)