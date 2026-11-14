import os
import uuid
from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploaded_images')
# Limit upload size to prevent resource exhaustion (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

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

        # Use secure_filename to prevent path traversal via the original filename
        original_filename = secure_filename(file.filename)
        ext = os.path.splitext(original_filename)[1]
        
        # Ensure extension is safe and not empty
        if not ext:
            ext = '.bin'
            
        # Generate a cryptographically secure unique ID for the filename
        # This prevents users from guessing other filenames or manipulating paths
        image_id = str(uuid.uuid4())
        filename = f"{image_id}{ext}"
        
        # Resolve absolute path and verify it is within the UPLOAD_FOLDER
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.abspath(filepath).startswith(UPLOAD_FOLDER):
            return jsonify({"error": "Invalid file path"}), 400
        
        file.save(filepath)
        
        # Metadata storage for mapping (simple append)
        # We only store the UUID and extension, both of which are controlled/validated
        with open(os.path.join(UPLOAD_FOLDER, "metadata.txt"), "a") as f:
            f.write(f"{image_id}:{ext}\n")

        return jsonify({"id": image_id}), 200

    except Exception:
        # Generic error message to avoid leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Serve the image file.
    """
    try:
        # Validate imageId to prevent path traversal (allow only alphanumeric/hyphens)
        # This ensures the user cannot pass '..' or absolute paths in the URL
        if not all(c.isalnum() or c == '-' for c in imageId):
            return jsonify({"error": "Invalid image ID"}), 400

        target_file = None
        # Iterate through directory to find the file starting with the UUID
        # This avoids using user input directly in a file path construction
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(imageId) and filename != "metadata.txt":
                target_file = filename
                break
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # send_from_directory is designed to prevent path traversal
        # as_attachment=False ensures the browser attempts to render the image
        return send_from_directory(
            UPLOAD_FOLDER, 
            target_file, 
            as_attachment=False
        )

    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)