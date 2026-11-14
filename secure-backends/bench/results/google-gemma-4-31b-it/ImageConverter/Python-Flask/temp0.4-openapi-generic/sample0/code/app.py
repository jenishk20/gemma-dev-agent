import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, send_file, render_template_string, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>GIF Creator</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; line-height: 1.6; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; }
        input[type="text"], input[type="number"] { width: 100%; padding: 8px; box-sizing: border-box; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; border-radius: 4px; }
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
        delay = request.form.get('delay', '10')
        append_reverted = request.form.get('appendReverted') == 'true'

        if not files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        # Validate target_size format to prevent shell injection (expecting WxH)
        if not (target_size.isalnum() or any(c in target_size for c in 'x')):
            # Basic check: ensure it looks like '500x500'
            pass 
        
        # Strict validation for target_size to prevent command injection
        import re
        if not re.match(r'^\d+x\d+$', target_size):
            return jsonify({"error": "Invalid targetSize format. Use WxH (e.g. 500x500)"}), 400
        
        # Validate delay is an integer
        try:
            delay_int = int(delay)
        except ValueError:
            return jsonify({"error": "Delay must be an integer"}), 400

        # 2. Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file in enumerate(files):
                filename = secure_filename(f"frame_{i}.png")
                path = os.path.join(tmpdir, filename)
                file.save(path)
                input_paths.append(path)

            # Handle appendReverted logic
            if append_reverted and len(input_paths) > 1:
                # Append images in reverse order, excluding the first and last to avoid duplicates
                # e.g. [1, 2, 3] -> [1, 2, 3, 2]
                reverted_paths = input_paths[-2::-1]
                # We need to save these as separate files for ImageMagick
                for i, path in enumerate(reverted_paths):
                    rev_path = os.path.join(tmpdir, f"rev_{i}.png")
                    shutil.copy(path, rev_path)
                    input_paths.append(rev_path)

            output_gif = os.path.join(tmpdir, "result.gif")

            # 3. Build ImageMagick command
            # -delay is in ticks. Default is 1/100th of a second. 
            # To get ms, we divide by 10.
            delay_ticks = str(delay_int // 10)
            
            # Command: convert -delay <ticks> -resize <size> <inputs> <output>
            # We use a list for subprocess.run to avoid shell=True and prevent injection
            cmd = [
                "convert",
                "-delay", delay_ticks,
                "-resize", target_size,
                *input_paths,
                output_gif
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return jsonify({"error": f"ImageMagick error: {result.stderr}"}), 500

            # 4. Return the generated GIF
            return send_file(output_gif, mimetype='image/gif')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)