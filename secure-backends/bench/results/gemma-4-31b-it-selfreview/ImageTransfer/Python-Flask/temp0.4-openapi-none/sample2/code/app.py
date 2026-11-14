import os
import uuid
from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploaded_images')
# Limit upload size to 16MB to prevent resource exhaustion (DoS)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Use secure_filename to prevent path traversal via the original filename
        filename = secure_filename(file.filename)
        extension = os.path.splitext(filename)[1]
        
        # Generate a cryptographically secure unique ID
        image_id = str(uuid.uuid4())
        
        # Construct filename using the generated ID, not the user-provided name
        save_filename = f"{image_id}{extension}"
        
        # Final path validation: ensure the file is saved strictly within UPLOAD_FOLDER
        file_path = os.path.join(UPLOAD_FOLDER, save_filename)
        if not file_path.startswith(UPLOAD_FOLDER):
            return jsonify({"error": "Invalid file path"}), 400

        file.save(file_path)
        return jsonify({"id": image_id}), 200

    except Exception:
        # Generic error to avoid leaking internal stack traces/details
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    try:
        # Sanitize imageId to prevent path traversal (remove any path separators)
        # The schema defines imageId as a string; we ensure it's treated as a simple token.
        safe_id = secure_filename(imageId)
        if safe_id != imageId:
            return jsonify({"error": "Invalid image ID"}), 400

        # List directory and find the file starting with the safe_id
        # This avoids passing user input directly into a file path for open() or send_from_directory
        files = os.listdir(UPLOAD_FOLDER)
        target_file = None
        
        for f in files:
            if f.startswith(safe_id):
                target_file = f
                break
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # send_from_directory is used with a fixed directory and a validated filename.
        # as_attachment=False ensures it's viewed in browser.
        return send_from_directory(
            UPLOAD_FOLDER, 
            target_file, 
            as_attachment=False
        )

    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)