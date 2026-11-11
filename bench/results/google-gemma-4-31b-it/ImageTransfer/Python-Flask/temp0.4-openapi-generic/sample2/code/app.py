import os
import uuid
import mimetypes
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# We don't use MAX_CONTENT_LENGTH here to be flexible, 
# but in production, you should set it (e.g., app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024)

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

        # Generate a unique ID for the image to prevent filename collisions and directory traversal
        image_id = str(uuid.uuid4())
        
        # Preserve original extension for mimetype detection
        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1]
        
        # Save file as the UUID to prevent users from guessing other filenames
        # and to avoid security risks associated with user-provided filenames
        filename = f"{image_id}{extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(file_path)
        
        return jsonify({"id": image_id}), 200

    except Exception as e:
        app.logger.error(f"Upload error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Serve the image based on the provided ID.
    """
    try:
        # To prevent directory traversal, we sanitize the imageId
        # and search for any file that starts with that UUID in the upload folder
        safe_id = secure_filename(imageId)
        
        # Find the file that starts with the given ID
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(safe_id)), None)
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404
        
        # Determine the mimetype of the file
        mime_type, _ = mimetypes.guess_type(target_file)
        
        # send_from_directory is secure against directory traversal
        # as_attachment=False ensures the browser tries to render it rather than download it
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            mimetype=mime_type,
            as_attachment=False
        )

    except Exception as e:
        app.logger.error(f"Retrieval error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)