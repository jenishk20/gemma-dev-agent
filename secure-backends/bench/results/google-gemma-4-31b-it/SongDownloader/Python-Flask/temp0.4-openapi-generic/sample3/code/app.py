import os
from flask import Flask, request, send_from_directory, abort, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = "/var/songs"

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that file's content.
    """
    # Validate that the request contains JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input: Request body must be JSON"}), 400

    # Extract filename from request body
    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input: 'filename' is required and must be a string"}), 400

    # Security: Prevent Directory Traversal attacks
    # secure_filename removes characters like '../' to ensure the file is within the target directory
    safe_filename = secure_filename(filename)
    
    if not safe_filename:
        return jsonify({"error": "Invalid filename provided"}), 400

    # Construct the full path and verify the file exists
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)
    
    # Double check that the resulting path is actually inside the SONGS_DIRECTORY
    # (Additional layer of security beyond secure_filename)
    if not os.path.abspath(file_path).startswith(os.path.abspath(SONGS_DIRECTORY)):
        return jsonify({"error": "Invalid file path"}), 400

    if not os.path.exists(file_path):
        abort(404, description="File does not exist")

    # send_from_directory is the recommended way to serve files in Flask.
    # It handles the range requests (streaming) and sets the correct Content-Type.
    try:
        return send_from_directory(
            directory=SONGS_DIRECTORY, 
            path=safe_filename, 
            mimetype='audio/mpeg'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure the directory exists to avoid startup crashes in some environments, 
    # though in production /var/songs should be pre-configured.
    if not os.path.exists(SONGS_DIRECTORY):
        # We don't create it here to avoid permission errors, 
        # but we log it or let the 404 handle it.
        pass

    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)