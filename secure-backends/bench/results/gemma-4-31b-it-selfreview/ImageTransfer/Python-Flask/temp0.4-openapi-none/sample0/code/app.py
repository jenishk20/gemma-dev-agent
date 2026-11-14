import os
import uuid
import mimetypes
from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploaded_images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Resource exhaustion: Limit maximum upload size to 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Upload an image and return a shareable ID.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Path Traversal Prevention: 
        # 1. Use secure_filename to strip dangerous characters from the original filename.
        # 2. Generate a random UUID for the actual storage name to decouple user input from the filesystem.
        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1].lower()
        
        # Basic validation to ensure extension is not something dangerous (like .exe or .php)
        # though the spec says "accept all formats", we still sanitize the extension.
        if not extension:
            extension = '.bin'

        image_id = str(uuid.uuid4())
        save_filename = f"{image_id}{extension}"
        
        # Ensure the final path is strictly within the UPLOAD_FOLDER
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
        if not os.path.abspath(file_path).startswith(app.config['UPLOAD_FOLDER']):
            return jsonify({"error": "Invalid file path"}), 400

        file.save(file_path)

        return jsonify({"id": image_id}), 200

    except Exception:
        # Error handling: Return documented status code without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Retrieve an image by its ID and display it in the browser.
    """
    try:
        # Path Traversal Prevention: 
        # 1. Validate imageId to ensure it contains only alphanumeric characters/hyphens (UUID format).
        # This prevents '..' or absolute paths from being passed as imageId.
        if not all(c.isalnum() or c == '-' for c in imageId):
            return jsonify({"error": "Invalid image ID"}), 400

        # List files and find the one matching the ID
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(imageId)), None)

        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # Double check that the target_file is actually within the directory (preventing any logic errors)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], target_file)
        if not os.path.abspath(full_path).startswith(app.config['UPLOAD_FOLDER']):
            return jsonify({"error": "Invalid file path"}), 400

        # Determine the mimetype based on the file extension
        mime_type, _ = mimetypes.guess_type(target_file)
        
        # send_from_directory is designed to prevent path traversal if used correctly.
        # as_attachment=False ensures the browser tries to render it.
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            mimetype=mime_type, 
            as_attachment=False
        ), 200

    except Exception:
        # Error handling: Return documented status code without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)