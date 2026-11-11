import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Security configuration: Limit upload size to 100MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/extract', methods=['POST'])
def extract_frame():
    """
    Extracts a specific frame from an uploaded video using ffmpeg.
    """
    # Validate request content type
    if not request.content_type == 'multipart/form-data':
        return jsonify({"error": "Content-Type must be multipart/form-data"}), 400

    # Extract parameters from form data
    video_file = request.files.get('video')
    frame_number_str = request.form.get('frameNumber')
    # videoFileName is provided in the schema but not strictly needed for processing
    # as we use a temporary file.

    if not video_file or not frame_number_str:
        return jsonify({"error": "Missing required fields: video or frameNumber"}), 400

    try:
        frame_number = int(frame_number_str)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    if frame_number < 0:
        return jsonify({"error": "frameNumber cannot be negative"}), 400

    # Use a temporary directory to handle the file securely
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input_video")
        output_path = os.path.join(tmpdir, "output_frame.png")
        
        # Save the uploaded file
        video_file.save(input_path)

        # ffmpeg command: 
        # -i: input file
        # -vf "select=eq(n\,X)": select frame X (0-indexed)
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'select=eq(n\\,{frame_number})',
                '-vframes', '1',
                '-f', 'image2',
                output_path
            ]
            
            # Run ffmpeg. stderr is captured to check for errors.
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Check if the output file was actually created and has size > 0
            # ffmpeg might return 0 even if the frame index was out of bounds
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404

            return send_file(output_path, mimetype='image/png')

        except subprocess.CalledProcessError as e:
            # If ffmpeg fails, it's likely the frame index is out of range or file is corrupt
            return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)