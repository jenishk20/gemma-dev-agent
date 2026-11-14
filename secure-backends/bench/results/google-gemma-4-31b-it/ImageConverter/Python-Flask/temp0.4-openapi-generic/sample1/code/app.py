import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, send_file, jsonify, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>GIF Creator</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input[type="text"], input[type="number"] { width: 100%; padding: 8px; box-sizing: border-box; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
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
        # 1. Validate Input
        if 'images' not in request.files:
            return jsonify({"error": "No images provided"}), 400
        
        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            return jsonify({"error": "No images selected"}), 400

        target_size = request.form.get('targetSize')
        if not target_size:
            return jsonify({"error": "targetSize is required"}), 400

        # Validate target_size format to prevent command injection (expecting WxH)
        if not all(c.isdigit() or c == 'x' for c in target_size) or 'x' not in target_size:
            return jsonify({"error": "Invalid targetSize format. Use WxH (e.g. 500x500)"}), 400

        delay = request.form.get('delay', '10')
        if not delay.isdigit():
            delay = '10'
        
        append_reverted = request.form.get('appendReverted', 'false').lower() == 'true'

        # 2. Process files in a temporary directory
        with tempfile.mkdtemp() as tmp_dir:
            input_paths = []
            for i, file in enumerate(files):
                filename = secure_filename(f"frame_{i}.img")
                path = os.path.join(tmp_dir, filename)
                file.save(path)
                input_paths.append(path)

            # Handle Reverted frames
            if append_reverted and len(input_paths) > 1:
                # Append images in reverse order, excluding the first and last to avoid duplicates at the pivot
                reverted = input_paths[-2:0:-1]
                input_paths.extend(reverted)

            output_gif = os.path.join(tmp_dir, "result.gif")
            
            # 3. Construct ImageMagick command
            # -delay is in ticks (usually 1/100th of a second), so ms / 10
            delay_ticks = str(int(delay) // 10)
            
            # Using a list for subprocess.run to avoid shell=True and prevent injection
            cmd = [
                "convert",
                "-delay", delay_ticks,
                "-loop", "0",
                "-resize", target_size,
                *input_paths,
                output_gif
            ]

            # Execute conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({"error": f"ImageMagick error: {result.stderr}"}), 500

            return send_file(output_gif, mimetype='image/gif')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)