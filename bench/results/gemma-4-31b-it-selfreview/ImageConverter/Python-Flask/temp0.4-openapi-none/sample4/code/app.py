import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, send_file, render_template_string, jsonify

app = Flask(__name__)

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
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; border-radius: 4px; }
        .btn:hover { background: #0056b3; }
        #result { margin-top: 20px; text-align: center; }
        img { max-width: 100%; border: 1px solid #ccc; }
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
            <label>Target Size (e.g., 500x500):</label>
            <input type="text" name="targetSize" placeholder="500x500" required>
        </div>
        <div class="form-group">
            <label>Delay (ms):</label>
            <input type="number" name="delay" value="100">
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" name="appendReverted" value="true"> Append Reverted Version (Ping-Pong)
            </label>
        </div>
        <button type="submit" class="btn">Create GIF</button>
    </form>
    <div id="result"></div>
</body>
</html>
"""

# Resource exhaustion limits
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit for total request body
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
MAX_IMAGES = 50  # Limit number of frames to prevent resource exhaustion

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/create-gif', methods=['POST'])
def create_gif():
    try:
        # 1. Extract and validate parameters
        images_files = request.files.getlist('images')
        target_size = request.form.get('targetSize')
        delay_raw = request.form.get('delay', '10')
        append_reverted = request.form.get('appendReverted', 'false').lower() == 'true'

        if not images_files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        if len(images_files) > MAX_IMAGES:
            return jsonify({"error": f"Too many images. Maximum allowed is {MAX_IMAGES}"}), 400

        # Validate targetSize format to prevent command injection or ImageMagick exploits
        # Expected format: WIDTHxHEIGHT (e.g. 500x500)
        import re
        if not re.match(r'^\d+x\d+$', target_size):
            return jsonify({"error": "Invalid targetSize format. Expected widthxheight (e.g. 500x500)"}), 400

        # Validate delay is an integer
        try:
            delay_val = int(delay_raw)
            if delay_val < 0: raise ValueError()
        except ValueError:
            return jsonify({"error": "Invalid delay value. Must be a non-negative integer"}), 400

        # 2. Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file in enumerate(images_files):
                # SECURITY: Ignore the user-provided filename entirely to prevent path traversal
                # We generate our own safe filename within the temp directory.
                safe_name = f"frame_{i}.tmp"
                path = os.path.join(tmpdir, safe_name)
                file.save(path)
                input_paths.append(path)

            # Handle "appendReverted" logic
            if append_reverted and len(input_paths) > 1:
                full_sequence = input_paths + input_paths[-2::-1]
            else:
                full_sequence = input_paths

            output_gif_path = os.path.join(tmpdir, "result.gif")
            
            # 3. Build ImageMagick command
            # Use a list for subprocess.run to avoid shell=True (prevents shell injection)
            delay_ticks = delay_val // 10
            
            cmd = [
                "convert",
                "-delay", str(delay_ticks),
                "-resize", target_size,
                "-loop", "0"
            ]
            cmd.extend(full_sequence)
            cmd.append(output_gif_path)

            # Execute the command with a timeout to prevent DoS
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Do not leak the full stderr to the user in production, 
                # but the schema allows a descriptive error. We provide a generic one.
                return jsonify({"error": "Image processing failed"}), 500

            # 4. Return the generated GIF
            return send_file(output_gif_path, mimetype='image/gif')

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Image processing timed out"}), 500
    except Exception as e:
        # Generic error handling to avoid leaking internal stack traces
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)