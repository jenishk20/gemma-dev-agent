import os
import uuid
import mimetypes
from flask import Flask, request, send_from_directory, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

        # Generate a unique ID for the image to prevent collisions and hide original filenames
        image_id = str(uuid.uuid4())
        
        # Preserve the original extension to maintain the correct mimetype
        filename = file.filename
        extension = os.path.splitext(filename)[1]
        save_filename = f"{image_id}{extension}"
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
        file.save(file_path)

        return jsonify({"id": image_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<imageId>', methods=['GET'])
def get_image(imageId):
    """
    Retrieve an image by its ID and display it in the browser.
    """
    try:
        # Find the file that starts with the imageId in the upload folder
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(imageId)), None)

        if target_file is None:
            return jsonify({"error": "Image not found"}), 404

        # Determine the mimetype based on the file extension
        mime_type, _ = mimetypes.guess_type(target_file)
        
        # send_from_directory handles the streaming of the file.
        # as_attachment=False ensures the browser tries to render it rather than download it.
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            target_file, 
            mimetype=mime_type, 
            as_attachment=False
        ), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)