import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, send_file, jsonify, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Resource limits
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit for total request size
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GIF Creator</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; line-height: 1.6; }
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
                <input type="checkbox" name="appendReverted" value="true"> Append Reverted (Ping-Pong effect)
            </label>
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
        # 1. Extract and validate inputs
        files = request.files.getlist('images')
        target_size = request.form.get('targetSize')
        delay_raw = request.form.get('delay', '10')
        append_reverted = request.form.get('appendReverted') == 'true'

        if not files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        # Validate targetSize format to prevent command injection or ImageMagick exploits
        # Expected format: widthxheight (e.g., 500x500)
        import re
        if not re.match(r'^\d+x\d+$', target_size):
            return jsonify({"error": "Invalid targetSize format. Expected widthxheight (e.g. 500x500)"}), 400

        # Validate delay is an integer
        try:
            delay_val = int(delay_raw)
            if delay_val < 0:
                raise ValueError
        except ValueError:
            return jsonify({"error": "Invalid delay value. Must be a non-negative integer"}), 400

        # Limit number of images to prevent resource exhaustion
        if len(files) > 100:
            return jsonify({"error": "Too many images. Maximum allowed is 100"}), 400

        # 2. Setup temporary directory for processing
        # Use tempfile.TemporaryDirectory for automatic cleanup
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_paths = []
            for i, file in enumerate(files):
                # secure_filename is used, but we also control the extension and name strictly
                filename = f"frame_{i}.png"
                path = os.path.join(tmp_dir, filename)
                
                # Ensure the path is actually inside the tmp_dir (Path Traversal check)
                if not os.path.abspath(path).startswith(os.path.abspath(tmp_dir)):
                    return jsonify({"error": "Invalid file path"}), 400
                
                file.save(path)
                input_paths.append(path)

            # Handle "appendReverted" logic
            if append_reverted and len(input_paths) > 1:
                reversed_paths = input_paths[::-1]
                input_paths.extend(reversed_paths[1:-1])

            output_gif_path = os.path.join(tmp_dir, "result.gif")

            # 3. Construct ImageMagick command
            # -delay is in ticks (1/100th of a second)
            delay_ticks = str(delay_val // 10)
            
            # Use a list for subprocess.run to avoid shell=True and shell injection
            cmd = [
                "convert",
                "-delay", delay_ticks,
                "-resize", target_size,
                *input_paths,
                output_gif_path
            ]

            # Execute conversion with a timeout to prevent DoS
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # We do not leak the full stderr to the user to avoid leaking internal paths or logic
                return jsonify({"error": "Image processing failed"}), 500

            # 4. Return the resulting GIF
            return send_file(output_gif_path, mimetype='image/gif')

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Image processing timed out"}), 500
    except Exception:
        # Generic error to avoid leaking stack traces
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000, debug=False)