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
        body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; }
        input[type="text"], input[type="number"] { width: 100%; padding: 8px; box-sizing: border-box; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; border-radius: 4px; }
        .btn:hover { background: #0056b3; }
        #result { margin-top: 20px; text-align: center; }
        img { max-width: 100%; height: auto; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>GIF Creator</h1>
    <form action="/create-gif" method="post" enctype="multipart/form-data">
        <div class="form-group">
            <label>Images (Select multiple):</label>
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
    <div id="result"></div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/create-gif', methods=['POST'])
def create_gif():
    try:
        # 1. Validate Inputs
        if 'images' not in request.files:
            return jsonify({"error": "No images provided"}), 400
        
        files = request.files.getlist('images')
        if not files or any(f.filename == '' for f in files):
            return jsonify({"error": "No valid images uploaded"}), 400

        target_size = request.form.get('targetSize')
        if not target_size:
            return jsonify({"error": "targetSize is required"}), 400

        # Validate targetSize format (widthxheight) to prevent shell injection
        if not (len(target_size) <= 20 and target_size.replace('x', '').isdigit()):
             return jsonify({"error": "Invalid targetSize format. Use WxH (e.g. 500x500)"}), 400

        try:
            delay = int(request.form.get('delay', 10))
        except ValueError:
            return jsonify({"error": "delay must be an integer"}), 400

        append_reverted = request.form.get('appendReverted', 'false').lower() == 'true'

        # 2. Setup Temporary Directory
        temp_dir = tempfile.mkdtemp()
        try:
            input_paths = []
            for i, file in enumerate(files):
                filename = secure_filename(f"frame_{i}.img")
                path = os.path.join(temp_dir, filename)
                file.save(path)
                input_paths.append(path)

            # Handle reverted sequence
            if append_reverted and len(input_paths) > 1:
                # Append images in reverse order (excluding first and last to avoid duplicates if desired, 
                # but standard "reverted" usually means full reverse)
                reverted_paths = input_paths[::-1]
                # To avoid double frames at the ends, we could slice: reverted_paths[1:-1]
                # But for a simple implementation, we just append the reverse.
                input_paths.extend(reverted_paths)

            output_path = os.path.join(temp_dir, "result.gif")

            # 3. Build ImageMagick Command
            # -delay is in hundredths of a second in ImageMagick
            im_delay = int(delay / 10) 
            
            # Using a list for subprocess.run to avoid shell=True (Security Best Practice)
            cmd = [
                "convert",
                "-delay", str(im_delay),
                "-loop", "0",
                "-resize", target_size,
            ]
            cmd.extend(input_paths)
            cmd.append(output_path)

            # Execute conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({"error": f"ImageMagick error: {result.stderr}"}), 500

            # 4. Return the GIF
            return send_file(output_path, mimetype='image/gif')

        finally:
            # Cleanup temp files
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)