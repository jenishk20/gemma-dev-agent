import os
import subprocess
import tempfile
import re
from flask import Flask, request, send_file, render_template_string, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Security Constants
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit to prevent resource exhaustion
MAX_IMAGES = 50  # Limit number of frames to prevent CPU/RAM exhaustion
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GIF Creator</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; line-height: 1.6; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; }
        input[type="text"], input[type="number"] { width: 100%; padding: 8px; box-sizing: border-box; }
        .btn { background: #007BFF; color: white; padding: 10px 20px; border: none; cursor: pointer; border-radius: 4px; }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>GIF Creator</h1>
    <form action="/create-gif" method="post" enctype="multipart/form-data">
        <div class="form-group">
            <label>Images:</label>
            <input type="file" name="images" multiple required>
        </div>
        <div class="form-group">
            <label>Target Size (WxH):</label>
            <input type="text" name="targetSize" placeholder="500x500" required>
        </div>
        <div class="form-group">
            <label>Delay (ms):</label>
            <input type="number" name="delay" value="100">
        </div>
        <div class="form-group">
            <input type="checkbox" name="appendReverted" value="true">
            <label style="display:inline">Append Reverted Version (Ping-Pong)</label>
        </div>
        <button type="submit" class="btn">Create GIF</button>
    </form>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/create-gif', methods=['POST'])
def create_gif():
    try:
        # 1. Extract and Validate Parameters
        images_files = request.files.getlist('images')
        target_size = request.form.get('targetSize', '').strip()
        delay_raw = request.form.get('delay', '10').strip()
        append_reverted = request.form.get('appendReverted') == 'true'

        # Basic presence check
        if not images_files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        # Resource Exhaustion: Limit number of images
        if len(images_files) > MAX_IMAGES:
            return jsonify({"error": f"Too many images. Maximum allowed is {MAX_IMAGES}"}), 400

        # Input Validation: targetSize must be in format WxH (digits only)
        # This prevents command injection/argument injection into ImageMagick
        if not re.match(r'^\d+x\d+$', target_size):
            return jsonify({"error": "Invalid targetSize format. Expected WxH (e.g. 500x500)"}), 400

        # Input Validation: delay must be an integer
        try:
            delay_val = int(delay_raw)
            if delay_val < 0: raise ValueError()
        except ValueError:
            return jsonify({"error": "Invalid delay. Must be a non-negative integer"}), 400

        # 2. Secure File Handling
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file in enumerate(images_files):
                # secure_filename removes '..' and absolute paths
                filename = secure_filename(f"frame_{i}_{file.filename}")
                if not filename:
                    filename = f"frame_{i}.tmp"
                
                filepath = os.path.join(tmpdir, filename)
                # Ensure the path is actually inside the temp directory (Path Traversal check)
                if not os.path.abspath(filepath).startswith(os.path.abspath(tmpdir)):
                    return jsonify({"error": "Invalid filename provided"}), 400
                
                file.save(filepath)
                input_paths.append(filepath)

            # Handle reverted version
            if append_reverted and len(input_paths) > 1:
                reverted_paths = input_paths[-2:0:-1]
                input_paths.extend(reverted_paths)

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # ImageMagick 'convert' command
            # We use a list for subprocess.run (shell=False by default) to prevent shell injection.
            # All variables passed here are now validated (target_size is regexed, delay is int).
            im_delay = delay_val // 10
            
            cmd = [
                "convert",
                "-delay", str(im_delay),
                "-loop", "0",
                "-resize", target_size,
            ] + input_paths + [output_gif]

            # Execute conversion with a timeout to prevent DoS via resource exhaustion
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                # Do not leak full stderr to user to avoid leaking internal paths/versions
                return jsonify({"error": "Image processing failed"}), 500

            return send_file(output_gif, mimetype='image/gif')

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Processing timed out"}), 500
    except Exception:
        # Generic error to avoid leaking stack traces
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)