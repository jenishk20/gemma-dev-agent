import os
import uuid
import mimetypes
from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
# Use an absolute path for the upload folder to ensure consistent path resolution
UPLOAD_FOLDER = os.path.abspath('uploaded_images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Resource Exhaustion: Bound uploaded file size (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Upload an image. Accept all formats.
    Returns a shareable link via an ID.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Security: Use secure_filename to prevent path traversal via the original filename
        # although we generate our own ID, we still sanitize the extension extraction.
        original_filename = secure_filename(file.filename)
        ext = os.path.splitext(original_filename)[1]
        
        # Security: Generate a cryptographically secure random ID (UUID4)
        image_id = str(uuid.uuid4())
        
        # Construct filename: only the UUID and the sanitized extension are used.
        # This prevents any user-supplied path characters from reaching the filesystem.
        filename = f"{image_id}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Double check that the resulting path is still within the UPLOAD_FOLDER
        if not os.path.abspath(filepath).startswith(UPLOAD_FOLDER):
            return jsonify({"error": "Invalid file path"}), 400

        file.save(filepath)
        
        return jsonify({"id": image_id}), 200

    except Exception:
        # Error handling: Return documented error status codes without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Share an image.
    Looks for a file starting with the imageId in the upload folder.
    """
    try:
        # Security: Validate imageId to prevent path traversal.
        # imageId should be a UUID string (alphanumeric and hyphens).
        # We reject any input containing '..' or '/' to prevent directory traversal.
        if '..' in imageId or '/' in imageId or '\\' in imageId:
            return jsonify({"error": "Invalid image ID"}), 400

        # Find the file that starts with the imageId
        # We list the directory and match the prefix.
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(imageId)), None)
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404
        
        # Security: Ensure target_file is just a filename and not a path
        # (os.listdir returns only filenames, but we verify for safety)
        if os.path.isabs(target_file) or '..' in target_file:
            return jsonify({"error": "Invalid file reference"}), 400

        # Guess the mimetype based on the extension to preserve original format
        mime_type, _ = mimetypes.guess_type(target_file)
        
        # send_from_directory is designed to prevent path traversal by 
        # validating that the requested file is within the specified directory.
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            mimetype=mime_type, 
            as_attachment=False
        )
        
    except Exception:
        # Error handling: Return documented error status codes without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)