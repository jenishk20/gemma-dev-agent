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
    # Validate that the request is JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input: Request body must be JSON"}), 400

    # Extract filename from the request body
    filename = data.get('filename')
    if not filename or not isinstance(filename, str):
        return jsonify({"error": "Invalid input: 'filename' is required and must be a string"}), 400

    try:
        # Security: prevent directory traversal attacks by ensuring the filename 
        # does not contain path separators (like ../)
        # send_from_directory handles basic security, but we ensure the filename is clean.
        safe_filename = os.path.basename(filename)
        
        if safe_filename != filename:
            return jsonify({"error": "Invalid input: Filename contains illegal characters"}), 400

        # Check if file exists before attempting to stream
        file_path = os.path.join(SONGS_DIRECTORY, safe_filename)
        if not os.path.isfile(file_path):
            return jsonify({"error": "File does not exist"}), 404

        # Stream the file from the directory
        # send_from_directory is the Flask-idiomatic way to stream files securely
        return send_from_directory(
            SONGS_DIRECTORY, 
            safe_filename, 
            mimetype='audio/mpeg'
        )

    except Exception as e:
        # Generic error handling for unexpected server issues
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)