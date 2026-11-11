import os
import uuid
import mimetypes
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_images'
# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# We disable the default MAX_CONTENT_LENGTH to allow various image sizes, 
# but in a production environment, you should set this (e.g., app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024)

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Upload an image and return a shareable link.
    """
    try:
        # Check if the multipart/form-data request contains the file
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Generate a unique ID for the image to prevent filename collisions and directory traversal
        image_id = str(uuid.uuid4())
        
        # Determine the original extension to preserve the file type
        # We use the original extension but store it under a random UUID for security
        ext = os.path.splitext(file.filename)[1].lower()
        filename = f"{image_id}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file
        file.save(filepath)
        
        # We store the mapping of ID to filename in the filename itself for simplicity in this implementation
        # In a real-world scenario, a database would map image_id -> actual_filename
        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Retrieve and display an image in the browser.
    """
    try:
        # To find the file, we look for any file in the upload folder that starts with the imageId
        # This allows us to support any extension without storing a database
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(imageId)), None)
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404
        
        # Guess the mimetype based on the extension
        mime_type, _ = mimetypes.guess_type(target_file)
        
        # send_from_directory is secure against directory traversal attacks
        # as_attachment=False ensures the browser tries to render the image rather than download it
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            mimetype=mime_type, 
            as_attachment=False
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)