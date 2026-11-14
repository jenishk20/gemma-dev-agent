import os
import uuid
import mimetypes
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploads')
# Limit upload size to 16MB to prevent resource exhaustion (DoS)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def safe_path_join(base, filename):
    """
    Ensures the resulting path is contained within the base directory 
    to prevent path traversal attacks.
    """
    # secure_filename removes directory separators and '..'
    safe_name = secure_filename(filename)
    if not safe_name:
        return None
    
    final_path = os.path.abspath(os.path.join(base, safe_name))
    if not final_path.startswith(UPLOAD_FOLDER):
        return None
    return final_path

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

        # Generate a cryptographically secure unique ID
        image_id = str(uuid.uuid4())
        
        # Extract extension and validate it's not a path traversal attempt
        # We only keep the extension and discard the user's original filename for the storage path
        _, ext = os.path.splitext(file.filename)
        
        # Sanitize extension to prevent directory traversal or weird filenames
        # We only allow alphanumeric characters and a dot
        clean_ext = "".join([c for c in ext if c.isalnum() or c == '.'])
        if not clean_ext:
            clean_ext = '.bin'
            
        filename = f"{image_id}{clean_ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Final check that the generated path is still within the upload folder
        if not os.path.abspath(filepath).startswith(UPLOAD_FOLDER):
            return jsonify({"error": "Invalid filename"}), 400

        file.save(filepath)

        # Use a simple mapping file. We use the UUID as the key.
        # We strip any potential CR/LF from the ID just in case, though uuid4 is safe.
        safe_id = image_id.replace('\n', '').replace('\r', '')
        with open(os.path.join(UPLOAD_FOLDER, "mapping.txt"), "a") as f:
            f.write(f"{safe_id}:{filename}\n")

        return jsonify({"id": safe_id}), 200

    except Exception:
        # Generic error to avoid leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Retrieve and display an image in the browser.
    """
    try:
        # Sanitize imageId to prevent path traversal or injection into the mapping file search
        # Only allow characters typical of a UUID
        safe_id = "".join([c for c in imageId if c.isalnum() or c == '-'])
        
        actual_filename = None
        mapping_path = os.path.join(UPLOAD_FOLDER, "mapping.txt")
        
        if os.path.exists(mapping_path):
            with open(mapping_path, "r") as f:
                for line in f:
                    # Split only on the first colon to prevent issues with filenames containing colons
                    parts = line.strip().split(":", 1)
                    if len(parts) == 2:
                        id_part, file_part = parts
                        if id_part == safe_id:
                            actual_filename = file_part
                            break
        
        if not actual_filename:
            return jsonify({"error": "Image not found"}), 404

        # Ensure the resolved filename is safe and stays within the UPLOAD_FOLDER
        full_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, actual_filename))
        if not full_path.startswith(UPLOAD_FOLDER) or not os.path.exists(full_path):
            return jsonify({"error": "Image not found"}), 404

        # Guess the mimetype based on the filename
        mimetype = mimetypes.guess_type(actual_filename)[0]
        if not mimetype:
            mimetype = 'application/octet-stream'

        # send_from_directory is generally safe, but we pass the sanitized filename
        # as_attachment=False ensures the browser attempts to render the image.
        return send_from_directory(
            UPLOAD_FOLDER, 
            actual_filename, 
            mimetype=mimetype, 
            as_attachment=False
        )

    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)