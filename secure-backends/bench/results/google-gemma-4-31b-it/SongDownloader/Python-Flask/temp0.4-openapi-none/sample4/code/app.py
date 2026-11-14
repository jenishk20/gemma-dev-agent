import os
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = "/var/songs"

@app.route('/download', methods=['POST'])
def download_song():
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that file's content.
    """
    # Validate request body
    data = request.get_json(silent=True)
    if data is None or 'filename' not in data:
        return jsonify({"error": "Invalid input: filename is required"}), 400

    filename = data['filename']

    # Security: Prevent directory traversal attacks by normalizing the path 
    # and ensuring the resulting path is within the SONGS_DIRECTORY
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # Check if file exists and is actually within the intended directory
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return jsonify({"error": "File does not exist"}), 404

    try:
        # send_file handles the streaming of the file content and sets the correct headers
        return send_file(
            file_path,
            mimetype='audio/mpeg',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure the directory exists for the sake of the server starting, 
    # though in production this is managed by the system.
    if not os.path.exists(SONGS_DIRECTORY):
        try:
            os.makedirs(SONGS_DIRECTORY)
        except PermissionError:
            print(f"Warning: Could not create {SONGS_DIRECTORY}. Ensure the directory exists.")

    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)