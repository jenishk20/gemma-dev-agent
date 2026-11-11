import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Validate multipart/form-data
    if not request.files or 'video' not in request.files:
        return jsonify({"error": "Missing video file"}), 400

    video_file = request.files['video']
    frame_number = request.form.get('frameNumber')
    
    if frame_number is None:
        return jsonify({"error": "Missing frameNumber"}), 400
    
    try:
        frame_index = int(frame_number)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Create a temporary directory to handle the video and output image
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input_video")
        output_path = os.path.join(tmpdir, "frame.png")
        
        # Save the uploaded video to the temp directory
        video_file.save(video_path)

        # Use ffmpeg to extract the specific frame
        # -i: input file
        # -vf: video filter to select the specific frame index
        # -vframes 1: output exactly one frame
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n\\{,} {frame_index})',
                '-vframes', '1',
                '-f', 'image2',
                output_path
            ]
            
            # Run ffmpeg. stderr is captured to check for errors.
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 or not os.path.exists(output_path):
                return jsonify({"error": f"Frame at index {frame_index} could not be found."}), 404
            
            # Return the extracted image as a PNG
            return send_file(output_path, mimetype='image/png')
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)