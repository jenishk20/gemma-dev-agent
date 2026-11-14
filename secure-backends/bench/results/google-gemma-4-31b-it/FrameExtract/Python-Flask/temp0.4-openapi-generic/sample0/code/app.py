import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Validate request content type
    if not request.content_type.startswith('multipart/form-data'):
        return jsonify({"error": "Invalid content type. Expected multipart/form-data"}), 400

    # Extract form data
    video_file = request.files.get('video')
    frame_number_str = request.form.get('frameNumber')
    video_file_name = request.form.get('videoFileName')

    if not video_file or not frame_number_str:
        return jsonify({"error": "Missing required fields: video or frameNumber"}), 400

    try:
        frame_number = int(frame_number_str)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    if video_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(video_file.filename):
        return jsonify({"error": "Unsupported video format"}), 400

    # Secure the filename and save to a temporary location
    filename = secure_filename(video_file.filename)
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    
    try:
        video_file.save(video_path)
        
        # Create a temporary path for the output image
        output_image_path = os.path.join(UPLOAD_FOLDER, f"frame_{frame_number}_{filename}.png")

        # Use ffmpeg to extract the specific frame
        # -i: input file
        # -vf "select=eq(n\,X)": filter to select frame X (0-indexed)
        # -vframes 1: output exactly one frame
        # -f image2: output format
        cmd = [
            'ffmpeg', '-y', 
            '-i', video_path, 
            '-vf', f'select=eq(n\\,{frame_number})', 
            '-vframes', '1', 
            '-f', 'image2', 
            output_image_path
        ]

        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode != 0 or not os.path.exists(output_image_path):
            # If ffmpeg failed or the frame index was out of bounds
            return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404

        # Return the image file
        return send_file(output_image_path, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup temporary files
        if os.path.exists(video_path):
            os.remove(video_path)
        # Note: In a production environment, you'd handle the output_image_path cleanup 
        # using a background task or a custom response wrapper since send_file 
        # needs the file to exist during transmission. 
        # For this small app, we accept the temporary file persistence until next run or manual clear.

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)