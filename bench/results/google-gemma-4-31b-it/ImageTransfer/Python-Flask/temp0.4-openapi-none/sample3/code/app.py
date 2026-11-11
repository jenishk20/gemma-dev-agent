import os
import uuid
import mimetypes
from flask import Flask, request, send_from_directory, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_images'
ALLOWED_EXTENSIONS = '*' # As per schema "Accept all formats"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Upload an image and return a shareable link.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Generate a unique ID for the image to prevent collisions and hide original filenames
        image_id = str(uuid.uuid4())
        
        # Determine extension from the original filename
        ext = os.path.splitext(file.filename)[1]
        if not ext:
            ext = '.bin' # Fallback for files without extensions
            
        filename = f"{image_id}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save the file
        file.save(filepath)
        
        # Store the mapping of image_id to the actual filename on disk
        # In a production app, this would be in a database. 
        # For this implementation, we'll store the mapping in a simple file or just use the ID as the filename.
        # To keep it simple and single-file, we save the file as {image_id}.ext and store the extension.
        # We use a simple trick: we save the original extension in a hidden file or just rely on mimetypes.
        # Actually, the most robust way without a DB is to save the file as the ID and store the extension in the filename.
        
        # We will save the mapping in a small text file to keep track of extensions
        with open(os.path.join(UPLOAD_FOLDER, "metadata.txt"), "a") as f:
            f.write(f"{image_id}:{ext}\n")

        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Serve the image file.
    """
    try:
        # Find the filename associated with the imageId
        target_file = None
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(imageId) and filename != "metadata.txt":
                target_file = filename
                break
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # Use send_from_directory which handles mimetypes automatically
        # as_attachment=False ensures the browser tries to render it rather than download it.
        return send_from_directory(
            UPLOAD_FOLDER, 
            target_file, 
            as_attachment=False
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)