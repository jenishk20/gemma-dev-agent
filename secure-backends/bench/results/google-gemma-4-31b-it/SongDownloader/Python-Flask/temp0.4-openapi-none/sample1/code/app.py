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
    # Validate that the request is JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input, expected JSON"}), 400

    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input, 'filename' is required and must be a string"}), 400

    # Security: Prevent Directory Traversal attacks
    # os.path.basename ensures we only look at the filename, not paths like ../../etc/passwd
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # Check if file exists and is actually within the songs directory
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return jsonify({"error": "File does not exist"}), 404

    try:
        # send_file handles the streaming of the file content
        # as_attachment=False allows the browser to stream/play it in-place
        # mimetype is set to audio/mpeg as per OpenAPI spec
        return send_file(
            file_path, 
            mimetype='audio/mpeg', 
            as_attachment=False
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure the directory exists for the sake of the demo, 
    # though in production /var/songs would be pre-configured.
    if not os.path.exists(SONGS_DIRECTORY):
        try:
            os.makedirs(SONGS_DIRECTORY)
        except PermissionError:
            print(f"Warning: Could not create {SONGS_DIRECTORY}. Please ensure it exists.")

    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)