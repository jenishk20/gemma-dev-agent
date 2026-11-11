import os
from flask import Flask, request, send_from_directory, jsonify

app = Flask(__name__)

# Configuration
SONGS_DIRECTORY = "/var/songs"

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

    # Validate that filename is provided and is a string
    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input: 'filename' is required and must be a string"}), 400

    # Security: Prevent directory traversal attacks by ensuring the filename 
    # does not contain path separators or ".."
    # send_from_directory handles some of this, but explicit check is safer.
    if os.path.basename(filename) != filename:
        return jsonify({"error": "Invalid filename provided"}), 400

    # Check if the file exists in the target directory
    file_path = os.path.join(SONGS_DIRECTORY, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File does not exist"}), 404

    # Stream the file from the directory
    # send_from_directory is the Flask-idiomatic way to serve files securely
    try:
        return send_from_directory(
            directory=SONGS_DIRECTORY, 
            path=filename, 
            mimetype='audio/mpeg'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)