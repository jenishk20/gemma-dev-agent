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
    # Get frameNumber from form data
    frame_number_str = request.form.get('frameNumber')
    
    if frame_number_str is None:
        return jsonify({"error": "Missing frameNumber"}), 400
    
    try:
        frame_number = int(frame_number_str)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to handle the upload and output
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input_video")
        output_path = os.path.join(tmpdir, "output_frame.png")
        
        # Save the uploaded video to disk
        video_file.save(video_path)

        # ffmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n,X)": selects the frame with index X
        # -vframes 1: output exactly one frame
        # -f image2pipe: output to stdout or a file
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'select=eq(n,{frame_number})',
            '-vframes', '1',
            '-f', 'image2',
            output_path,
            '-y' # Overwrite if exists
        ]

        try:
            # Run ffmpeg. stderr is used for logging; stdout is empty for this command
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if the output file was actually created
            if process.returncode != 0 or not os.path.exists(output_path):
                return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404
            
            # Return the image file
            return send_file(output_path, mimetype='image/png')
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)