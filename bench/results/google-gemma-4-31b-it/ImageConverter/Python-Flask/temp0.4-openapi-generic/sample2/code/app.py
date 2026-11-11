import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

def validate_size(size_str):
    """Validates that targetSize is in format WxH (e.g., 500x500)"""
    if not size_str or 'x' not in size_str:
        return False
    try:
        parts = size_str.split('x')
        if len(parts) != 2:
            return False
        int(parts[0])
        int(parts[1])
        return True
    except ValueError:
        return False

@app.route('/create-gif', methods=['POST'])
def create_gif():
    try:
        # 1. Extract and validate inputs
        if not request.files or 'images' not in request.files:
            return jsonify({"error": "Missing images in request"}), 400

        images = request.files.getlist('images')
        if not images:
            return jsonify({"error": "No images provided"}), 400

        target_size = request.form.get('targetSize')
        if not target_size or not validate_size(target_size):
            return jsonify({"error": "Invalid or missing targetSize. Expected format: WxH (e.g. 500x500)"}), 400

        # Delay: default 10, provided in ms. ImageMagick uses ticks (1/100s)
        delay_ms = request.form.get('delay', 10)
        try:
            delay_ticks = int(delay_ms) // 10
        except ValueError:
            return jsonify({"error": "Invalid delay value"}), 400

        # appendReverted: boolean check
        append_reverted = request.form.get('appendReverted', 'false').lower() == 'true'

        # 2. Create temporary directory for processing
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, img_file in enumerate(images):
                # Secure filename by ignoring the provided name and using a counter
                ext = os.path.splitext(img_file.filename)[1]
                # Basic extension validation
                if ext.lower() not in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                    return jsonify({"error": f"Unsupported image format: {ext}"}), 400
                
                path = os.path.join(tmpdir, f"frame_{i}{ext}")
                img_file.save(path)
                input_paths.append(path)

            # Handle the 'appendReverted' logic
            if append_reverted:
                # Append images in reverse order (excluding the last one to avoid duplicate center frame)
                # or just reverse the whole list. Usually, "reverted" means a ping-pong effect.
                # We skip the first and last to make the loop smooth, but for simplicity, we reverse all.
                reversed_paths = input_paths[::-1]
                # To avoid double frames at the ends, we slice the reversed list
                # If 3 frames [A, B, C], reverted would be [B, A]
                reverted_slice = input_paths[-2:0:-1] if len(input_paths) > 2 else []
                # For a simple implementation as per schema "append a reverted version":
                all_frames = input_paths + input_paths[::-1]
            else:
                all_frames = input_paths

            output_gif = os.path.join(tmpdir, "result.gif")

            # 3. Construct ImageMagick command
            # convert -delay <ticks> -resize <WxH> <files> <output>
            # We use a list for subprocess to prevent shell injection
            cmd = [
                "convert",
                "-delay", str(delay_ticks),
                "-resize", target_size,
                "-loop", "0"
            ]
            cmd.extend(all_frames)
            cmd.append(output_gif)

            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"ImageMagick error: {e.stderr.decode()}"}), 500

            # 4. Return the resulting GIF
            return send_file(output_gif, mimetype='image/gif')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)