import os
import uuid
import mimetypes
from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff'}

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    # The schema says "Accept all formats", but for safety and browser viewing, 
    # we check if it has an extension.
    return '.' in filename

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # Check if the multipart request contains the file field
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Generate a unique ID for the image to prevent collisions and hide original filenames
        image_id = str(uuid.uuid4())
        
        # Preserve the original extension
        filename = secure_filename(file.filename)
        extension = os.path.splitext(filename)[1]
        
        # Save the file with the unique ID as the filename
        save_filename = f"{image_id}{extension}"
        file_path = os.path.join(UPLOAD_FOLDER, save_filename)
        file.save(file_path)

        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    try:
        # We need to find the file that starts with the imageId in the upload folder
        # since we appended the original extension during upload.
        files = os.listdir(UPLOAD_FOLDER)
        target_file = None
        
        for f in files:
            if f.startswith(imageId):
                target_file = f
                break
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # send_from_directory handles the mimetype automatically based on extension.
        # as_attachment=False ensures the browser tries to render it rather than download it.
        return send_from_directory(
            UPLOAD_FOLDER, 
            target_file, 
            as_attachment=False
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)