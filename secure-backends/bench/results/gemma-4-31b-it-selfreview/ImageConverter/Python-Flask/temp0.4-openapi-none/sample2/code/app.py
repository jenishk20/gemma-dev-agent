import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Security: Limit request size to prevent resource exhaustion (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
        input[type="file"] { margin-top: 5px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }
        button:hover { background: #0056b3; }
        .result { margin-top: 20px; text-align: center; }
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
                <input type="checkbox" name="appendReverted" value="true"> Append Reverted (Ping-Pong)
            </label>
        </div>
        <button type="submit">Create GIF</button>
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
        # 1. Validate and get inputs
        files = request.files.getlist('images')
        target_size = request.form.get('targetSize')
        delay_raw = request.form.get('delay', '10')
        append_reverted = request.form.get('appendReverted') == 'true'

        if not files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        # Security: Validate targetSize format to prevent command injection/malformed args
        # Expected format: widthxheight (e.g., 500x500)
        import re
        if not re.match(r'^\d+x\d+$', target_size):
            return jsonify({"error": "Invalid targetSize format. Expected widthxheight (e.g. 500x500)"}), 400

        # Security: Validate delay is an integer
        try:
            delay_val = int(delay_raw)
            if delay_val < 0:
                raise ValueError()
        except ValueError:
            return jsonify({"error": "Invalid delay value. Must be a non-negative integer"}), 400

        # 2. Create temporary directory for processing
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for file in files:
                if file.filename == '':
                    continue
                
                # Security: Use secure_filename to prevent path traversal
                filename = secure_filename(file.filename)
                if not filename:
                    continue
                
                # Ensure the file is saved strictly inside the temporary directory
                # secure_filename removes '..' and absolute paths
                path = os.path.join(tmpdir, filename)
                file.save(path)
                input_paths.append(path)

            if not input_paths:
                return jsonify({"error": "No valid images uploaded"}), 400

            # Handle appendReverted logic
            if append_reverted:
                full_sequence = input_paths + input_paths[-2::-1]
            else:
                full_sequence = input_paths

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # Convert ms to ImageMagick ticks (1 tick = 10ms)
            im_delay = delay_val // 10

            # Security: Use a list for subprocess.run to avoid shell=True and shell injection
            # All inputs (target_size, im_delay) are now validated via regex/int cast
            cmd = [
                "convert",
                "-delay", str(im_delay),
                "-loop", "0",
                "-resize", target_size,
            ]
            cmd.extend(full_sequence)
            cmd.append(output_gif)

            # Security: Set a timeout to prevent resource exhaustion (DoS) via long-running processes
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Security: Do not leak full stderr to the user if it contains sensitive paths, 
                # but the OpenAPI spec requires an error message.
                return jsonify({"error": "Image processing failed"}), 500

            return send_file(output_gif, mimetype='image/gif')

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Processing timed out"}), 500
    except Exception:
        # Security: Generic error message to avoid leaking stack traces
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Security: Ensure we are not running in debug mode in production
    app.run(host='0.0.0.0', port=5000, debug=False)