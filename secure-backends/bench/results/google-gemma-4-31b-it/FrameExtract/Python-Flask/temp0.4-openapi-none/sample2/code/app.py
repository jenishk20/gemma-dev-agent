import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Extracting parameters from multipart/form-data
    video_file = request.files.get('video')
    frame_number = request.form.get('frameNumber')
    
    if not video_file or frame_number is None:
        return jsonify({"error": "Missing video file or frameNumber"}), 400

    try:
        frame_idx = int(frame_number)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Create a temporary directory to handle the upload and the output image
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input_video.mp4")
        output_path = os.path.join(tmpdir, "frame.png")
        
        # Save the uploaded video to the temporary path
        video_file.save(video_path)
        
        # Use ffmpeg to extract the specific frame
        # -i: input file
        # -vf "select=eq(n\,X)": filter to select frame X (0-indexed)
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'select=eq(n,{frame_idx})',
            '-vframes', '1',
            '-f', 'image2',
            output_path
        ]
        
        try:
            # Run ffmpeg command. stderr is captured to avoid cluttering logs, 
            # but check return code for success.
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 or not os.path.exists(output_path):
                return jsonify({"error": f"Frame at index {frame_idx} could not be found."}), 404
            
            # Return the extracted image as a PNG
            return send_file(output_path, mimetype='image/png')
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)