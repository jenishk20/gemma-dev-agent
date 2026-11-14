import os
import subprocess
import tempfile
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
        # 1. Extract parameters
        images_files = request.files.getlist('images')
        target_size = request.form.get('targetSize')
        delay = request.form.get('delay', '10')
        append_reverted = request.form.get('appendReverted') == 'true'

        if not images_files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        # 2. Create a temporary directory to store frames
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file in enumerate(images_files):
                filename = secure_filename(f"frame_{i}_{file.filename}")
                filepath = os.path.join(tmpdir, filename)
                file.save(filepath)
                input_paths.append(filepath)

            # Handle reverted version (ping-pong effect)
            if append_reverted and len(input_paths) > 1:
                # Add images in reverse order, excluding the first and last to avoid duplicates at the pivot
                reverted_paths = input_paths[-2:0:-1]
                input_paths.extend(reverted_paths)

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # ImageMagick 'convert' command:
            # -delay: time between frames (1/100th of a second in IM, so ms/10)
            # -resize: target size
            # -loop 0: infinite loop
            im_delay = int(delay) // 10
            
            cmd = [
                "convert",
                "-delay", str(im_delay),
                "-loop", "0",
                "-resize", target_size,
            ] + input_paths + [output_gif]

            # Execute conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({"error": f"ImageMagick error: {result.stderr}"}), 500

            return send_file(output_gif, mimetype='image/gif')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)