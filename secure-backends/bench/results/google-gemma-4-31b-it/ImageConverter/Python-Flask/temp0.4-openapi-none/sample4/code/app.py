import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, send_file, render_template_string, jsonify

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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/create-gif', methods=['POST'])
def create_gif():
    try:
        # 1. Extract parameters from request
        images_files = request.files.getlist('images')
        target_size = request.form.get('targetSize')
        delay = request.form.get('delay', '10')
        append_reverted = request.form.get('appendReverted', 'false').lower() == 'true'

        if not images_files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        # 2. Create a temporary directory to store images
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file in enumerate(images_files):
                # Save each uploaded file to the temp directory
                ext = os.path.splitext(file.filename)[1]
                path = os.path.join(tmpdir, f"frame_{i}{ext}")
                file.save(path)
                input_paths.append(path)

            # Handle "appendReverted" logic
            if append_reverted and len(input_paths) > 1:
                # Create copies of images in reverse order (excluding first and last to avoid double frames)
                # but for simplicity and standard GIF behavior, we just append the list reversed
                # excluding the last frame of the forward sequence and the first of the backward.
                reversed_paths = input_paths[-2:0:-1] 
                # If only 2 images, reversed_paths might be empty. Let's just do a full reverse minus the last.
                full_sequence = input_paths + input_paths[-2::-1]
            else:
                full_sequence = input_paths

            output_gif_path = os.path.join(tmpdir, "result.gif")
            
            # 3. Build ImageMagick command
            # -delay: time between frames (1/100th of a second in IM, but schema says ms)
            # IM delay is in ticks. Default is 100 ticks per second. 
            # To get ms, we use: delay_ticks = ms / 10
            try:
                delay_ticks = int(delay) // 10
            except ValueError:
                delay_ticks = 1

            cmd = [
                "convert",
                "-delay", str(delay_ticks),
                "-resize", target_size,
                "-loop", "0" # Infinite loop
            ]
            cmd.extend(full_sequence)
            cmd.append(output_gif_path)

            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({"error": f"ImageMagick error: {result.stderr}"}), 500

            # 4. Return the generated GIF
            return send_file(output_gif_path, mimetype='image/gif')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)