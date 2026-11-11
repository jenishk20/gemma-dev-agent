import os
from flask import Flask, request, send_from_directory, jsonify, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = '/var/songs'

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Expects a JSON body with a 'filename' property.
    """
    # Validate that the request is JSON
    if not request.is_json:
        return jsonify({"error": "Invalid input: Request body must be application/json"}), 400

    data = request.get_json()

    # Validate that 'filename' exists in the request body
    if not data or 'filename' not in data:
        return jsonify({"error": "Invalid input: 'filename' is required"}), 400

    filename = data.get('filename')

    # Security: Use secure_filename to prevent Directory Traversal attacks
    # secure_filename removes characters like '../' which could be used to access files outside the directory
    safe_filename = secure_filename(filename)

    if not safe_filename:
        return jsonify({"error": "Invalid filename provided"}), 400

    # Check if the file exists in the specified directory
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File does not exist"}), 404

    # send_from_directory is the recommended way to serve files from a directory
    # It provides additional security checks and handles the bytestream/mimetype automatically
    try:
        return send_from_directory(
            SONGS_DIRECTORY, 
            safe_filename, 
            mimetype='audio/mpeg'
        )
    except Exception as e:
        app.logger.error(f"Error streaming file: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Ensure the directory exists to prevent startup crashes in some environments, 
    # though in production /var/songs would be pre-configured.
    if not os.path.exists(SONGS_DIRECTORY):
        os.makedirs(SONGS_DIRECTORY, exist_ok=True)

    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)