import os
import uuid
import mimetypes
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Upload an image and return a shareable link.
    """
    try:
        # Check if the multipart/form-data request contains the file field
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Generate a unique ID for the image to prevent filename collisions and directory traversal
        image_id = str(uuid.uuid4())
        
        # Determine the original extension to preserve the file type
        filename = secure_filename(file.filename)
        extension = os.path.splitext(filename)[1]
        
        # Save the file with the UUID as the name
        save_filename = f"{image_id}{extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
        
        # Store the original filename/extension mapping if needed, 
        # but for this simple API, we just save the file.
        file.save(file_path)
        
        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<image_id>', methods=['GET'])
def get_image(image_id):
    """
    Retrieve and view an image in the browser.
    """
    try:
        # To prevent directory traversal, we only look for files that start with the provided UUID
        # We iterate through the upload folder to find the file matching the UUID
        target_file = None
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.startswith(image_id):
                target_file = filename
                break
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # Guess the mimetype based on the extension
        mimetype = mimetypes.guess_type(target_file)[0]
        if not mimetype:
            mimetype = 'application/octet-stream'

        # send_from_directory is secure against directory traversal attacks
        # as_attachment=False ensures the browser attempts to render it rather than download it
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            mimetype=mimetype, 
            as_attachment=False
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000, debug=False)