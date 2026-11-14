import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configure a temporary directory for processing
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/extract', methods=['POST'])
def extract_frame():
    """
    Extracts a specific frame from an uploaded video using ffmpeg.
    """
    # Validate that the necessary fields are present in the multipart request
    if 'video' not in request.files:
        return jsonify({"error": "Missing video file"}), 400
    
    video_file = request.files['video']
    frame_number_str = request.form.get('frameNumber')
    
    if not frame_number_str:
        return jsonify({"error": "Missing frameNumber"}), 400
    
    try:
        frame_number = int(frame_number_str)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # We ignore videoFileName from the request body for security (prevent path traversal)
    # and use a secure temporary file for the upload.
    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as input_tmp:
        video_file.save(input_tmp.name)
        input_path = input_tmp.name

    # Create a temporary path for the output image
    output_path = os.path.join(UPLOAD_FOLDER, f"frame_{frame_number}.png")
    
    try:
        # ffmpeg command: 
        # -i: input file
        # -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        cmd = [
            'ffmpeg',
            '-y', # Overwrite output file if it exists
            '-i', input_path,
            '-vf', f'select=eq(n\\,{frame_number})',
            '-vframes', '1',
            '-f', 'image2',
            output_path
        ]
        
        # Run ffmpeg. stderr is captured to check if the frame actually existed.
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0 or not os.path.exists(output_path):
            # If ffmpeg fails or the file wasn't created, the frame index might be out of range
            return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404

        # Return the image file
        return send_file(output_path, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup temporary files
        if os.path.exists(input_path):
            os.remove(input_path)
        # Note: In a production environment, you'd want a more robust cleanup 
        # for the output_path, perhaps using a background task or a unique ID.
        # For this small app, we'll leave it to the OS temp cleanup or overwrite.

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)