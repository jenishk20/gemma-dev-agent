import os
import uuid
import mimetypes
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_images'
# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# We don't strictly limit size here to allow "all formats", 
# but in production, MAX_CONTENT_LENGTH should be set.
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Upload an image and return a shareable ID.
    """
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Generate a unique ID for the image to prevent filename collisions 
        # and hide the original filename for security.
        image_id = str(uuid.uuid4())
        
        # Preserve the original extension for the filesystem and mimetype detection
        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1]
        
        # If no extension is found, we store it as is, but mimetype will be handled by the OS/mimetypes lib
        save_filename = f"{image_id}{extension}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
        
        # Save the file
        file.save(save_path)
        
        return jsonify({"id": image_id}), 200

    except Exception as e:
        app.logger.error(f"Upload error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/<image_id>', methods=['GET'])
def share_image(image_id):
    """
    Serve the image for viewing in the browser.
    """
    try:
        # To find the file, we need to check which file starts with the image_id
        # since we appended the extension during upload.
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(image_id)), None)
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404
        
        # send_from_directory is secure and prevents directory traversal attacks.
        # as_attachment=False ensures the browser tries to render the image 
        # instead of forcing a download.
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            as_attachment=False
        )
        
    except Exception as e:
        app.logger.error(f"Retrieval error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)