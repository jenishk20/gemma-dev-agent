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
    Expects JSON body: {"filename": "song.mp3"}
    """
    # Validate request content type
    if not request.is_json:
        return jsonify({"error": "Invalid input: Request body must be JSON"}), 400

    data = request.get_json()

    # Validate that filename is provided and is a string
    if not data or 'filename' not in data:
        return jsonify({"error": "Invalid input: 'filename' property is required"}), 400
    
    filename = data.get('filename')
    if not isinstance(filename, str):
        return jsonify({"error": "Invalid input: 'filename' must be a string"}), 400

    # Security: Use secure_filename to prevent Path Traversal attacks (e.g., ../../etc/passwd)
    # secure_filename strips directory separators and special characters
    safe_filename = secure_filename(filename)

    if not safe_filename:
        return jsonify({"error": "Invalid input: Filename is empty or invalid"}), 400

    # Check if file exists before attempting to send
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File does not exist"}), 404

    # send_from_directory is the secure way to serve files from a specific folder in Flask.
    # It further validates that the requested file is within the specified directory.
    try:
        return send_from_directory(
            SONGS_DIRECTORY, 
            safe_filename, 
            mimetype='audio/mpeg'
        )
    except Exception as e:
        return jsonify({"error": "An internal error occurred while streaming the file"}), 500

if __name__ == '__main__':
    # Ensure the songs directory exists to prevent startup crash, 
    # though in a real prod env this would be handled by infrastructure.
    if not os.path.exists(SONGS_DIRECTORY):
        os.makedirs(SONGS_DIRECTORY, exist_ok=True)
        
    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)