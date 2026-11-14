import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Validate request content type
    if not request.is_json and not request.form:
        return jsonify({"error": "Invalid request. Expected multipart/form-data"}), 400

    # Extract parameters from multipart/form-data
    video_file = request.files.get('video')
    frame_number = request.form.get('frameNumber')
    # videoFileName is provided in schema but not strictly needed for processing
    # video_file_name = request.form.get('videoFileName')

    if not video_file or frame_number is None:
        return jsonify({"error": "Missing required fields: video or frameNumber"}), 400

    try:
        frame_idx = int(frame_number)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to handle the upload and the output frame
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input_video")
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to disk
        video_file.save(video_path)

        # ffmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n\,X)": select frame with index X
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'select=eq(n\\,{frame_idx})',
            '-vframes', '1',
            '-f', 'image2',
            output_path
        ]

        try:
            # Run ffmpeg and capture output to check for success
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            
            # Check if the output file was actually created
            if result.returncode != 0 or not os.path.exists(output_path):
                return jsonify({"error": f"Frame at index {frame_idx} could not be found."}), 404

            # Return the extracted image as a PNG
            return send_file(output_path, mimetype='image/png')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "Processing timed out"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)