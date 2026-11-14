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
    # Validate that the video file is present
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files['video']
    
    # Validate frameNumber
    frame_number_str = request.form.get('frameNumber')
    if not frame_number_str or not frame_number_str.isdigit():
        return jsonify({"error": "Valid frameNumber is required"}), 400
    
    frame_number = int(frame_number_str)

    if video_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Secure the filename to prevent directory traversal attacks
    filename = secure_filename(video_file.filename)
    
    # Create a temporary directory for this specific request to avoid collisions
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, filename)
        output_image_path = os.path.join(tmpdir, "frame.png")
        
        # Save uploaded video to temp path
        video_file.save(video_path)

        # FFmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n\,{frame_number})',
                '-vframes', '1',
                '-f', 'image2',
                output_image_path
            ]
            
            # Run ffmpeg. stderr is captured to check for errors.
            result = subprocess.run(cmd, capture_output=True, text=True)

            # If ffmpeg failed or the output file wasn't created (frame index out of bounds)
            if result.returncode != 0 or not os.path.exists(output_image_path):
                return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404

            # Return the extracted image
            return send_file(output_image_path, mimetype='image/png')

        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)