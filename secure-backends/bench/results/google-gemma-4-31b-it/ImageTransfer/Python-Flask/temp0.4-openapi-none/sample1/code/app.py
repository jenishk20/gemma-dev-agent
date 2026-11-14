import os
import uuid
import mimetypes
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

        # If user does not select file, expected behavior is a bad request
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Generate a unique ID for the image to prevent collisions and hide original filename
        image_id = str(uuid.uuid4())
        
        # Determine the original extension to preserve the file type
        name, ext = os.path.splitext(file.filename)
        if not ext:
            # Fallback to guessing extension based on content if possible, 
            # but for this API we will just use a generic extension or the provided one.
            ext = '.bin'
            
        filename = f"{image_id}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save the file
        file.save(filepath)

        # Store the mapping of image_id to the actual filename on disk
        # In a production app, this would be in a database. 
        # Here we use the filename as the ID essentially, but we return the UUID.
        # To make retrieval easy, we save the mapping in a simple way:
        # We'll just store the extension in a sidecar file or just search for the prefix.
        # For simplicity in this single-file implementation, we save the mapping in a text file.
        with open(os.path.join(UPLOAD_FOLDER, "mapping.txt"), "a") as f:
            f.write(f"{image_id}:{filename}\n")

        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Retrieve and display an image in the browser.
    """
    try:
        # Look up the actual filename from the mapping file
        actual_filename = None
        mapping_path = os.path.join(UPLOAD_FOLDER, "mapping.txt")
        
        if os.path.exists(mapping_path):
            with open(mapping_path, "r") as f:
                for line in f:
                    id_part, file_part = line.strip().split(":", 1)
                    if id_part == imageId:
                        actual_filename = file_part
                        break
        
        if not actual_filename or not os.path.exists(os.path.join(UPLOAD_FOLDER, actual_filename)):
            return jsonify({"error": "Image not found"}), 404

        # Guess the mimetype based on the filename to ensure it's viewed in browser
        mimetype = mimetypes.guess_type(actual_filename)[0]
        if not mimetype:
            mimetype = 'application/octet-stream'

        # send_from_directory handles the response. 
        # as_attachment=False ensures the browser tries to render it rather than download.
        return send_from_directory(
            UPLOAD_FOLDER, 
            actual_filename, 
            mimetype=mimetype, 
            as_attachment=False
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)