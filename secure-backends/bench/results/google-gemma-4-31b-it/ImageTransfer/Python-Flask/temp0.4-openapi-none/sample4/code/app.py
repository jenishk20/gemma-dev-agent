import os
import uuid
import mimetypes
from flask import Flask, request, send_from_directory, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

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

        # Generate a unique ID for the image to prevent collisions and hide original filenames
        image_id = str(uuid.uuid4())
        
        # Determine the original extension
        ext = os.path.splitext(file.filename)[1]
        filename = f"{image_id}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file
        file.save(filepath)
        
        # Store the mapping of ID to actual filename in a simple way 
        # (In this implementation, we store the extension in the filename and use the ID as the key)
        # To retrieve it, we'll look for the file starting with the ID.
        
        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Share an image.
    Looks for a file starting with the imageId in the upload folder.
    """
    try:
        # Find the file that starts with the imageId
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(imageId)), None)
        
        if target_file is None:
            return jsonify({"error": "Image not found"}), 404
        
        # Guess the mimetype based on the extension to preserve original format
        mime_type, _ = mimetypes.guess_type(target_file)
        
        # send_from_directory handles the response. 
        # as_attachment=False ensures the browser attempts to render it rather than download it.
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            mimetype=mime_type, 
            as_attachment=False
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)