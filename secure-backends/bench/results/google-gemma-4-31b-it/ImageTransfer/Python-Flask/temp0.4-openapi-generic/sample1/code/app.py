import os
import uuid
import mimetypes
from flask import Flask, request, send_from_directory, jsonify, abort
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
    Upload an image and return a unique identifier.
    """
    try:
        # Check if the file part is present in the request
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # We generate a unique ID to prevent filename collisions and 
        # directory traversal attacks. We store the original extension.
        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1]
        
        # Generate a unique ID for the image
        image_id = str(uuid.uuid4())
        filename = f"{image_id}{extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save the file
        file.save(filepath)

        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Retrieve and serve the image by its ID.
    """
    try:
        # To find the file, we look for any file starting with the imageId in the upload folder
        # This allows us to support various extensions without storing a database of extensions.
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(imageId)), None)

        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # send_from_directory is secure against directory traversal
        # as_attachment=False ensures the browser attempts to render it rather than download it
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            as_attachment=False
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)