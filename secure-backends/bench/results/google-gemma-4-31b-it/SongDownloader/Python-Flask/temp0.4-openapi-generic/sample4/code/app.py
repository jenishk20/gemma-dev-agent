import os
from flask import Flask, request, send_from_directory, jsonify
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
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input: Request body must be JSON"}), 400

    filename = data.get('filename')

    # Validate that filename is provided and is a string
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input: 'filename' is required and must be a string"}), 400

    # SECURITY: Prevent Path Traversal attacks.
    # secure_filename removes directory separators and special characters.
    # This ensures the user cannot request files like '../../etc/passwd'.
    safe_filename = secure_filename(filename)
    
    if not safe_filename:
        return jsonify({"error": "Invalid filename provided"}), 400

    # Check if the file exists within the designated directory
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File does not exist"}), 404

    # send_from_directory is the secure way to serve files in Flask.
    # It ensures the requested file is within the specified directory.
    try:
        return send_from_directory(
            SONGS_DIRECTORY, 
            safe_filename, 
            mimetype='audio/mpeg'
        )
    except Exception as e:
        return jsonify({"error": "An error occurred while streaming the file"}), 500

if __name__ == '__main__':
    # Ensure the songs directory exists to prevent startup crashes, 
    # though in a production environment this would be handled by deployment scripts.
    if not os.path.exists(SONGS_DIRECTORY):
        # For demonstration purposes, we create it if it doesn't exist, 
        # but in a real /var/songs scenario, the app would likely run as a specific user.
        try:
            os.makedirs(SONGS_DIRECTORY, exist_ok=True)
        except OSError:
            print(f"Warning: Could not create {SONGS_DIRECTORY}. Ensure the app has permissions.")

    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)