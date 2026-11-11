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
        # 1. Extract and validate inputs
        files = request.files.getlist('images')
        target_size = request.form.get('targetSize')
        delay = request.form.get('delay', '10')
        append_reverted = request.form.get('appendReverted') == 'true'

        if not files or not target_size:
            return jsonify({"error": "Missing required fields: images and targetSize"}), 400

        # 2. Setup temporary directory for processing
        with tempfile.mkdtemp() as tmp_dir:
            input_paths = []
            for i, file in enumerate(files):
                filename = secure_filename(f"frame_{i}.png")
                path = os.path.join(tmp_dir, filename)
                file.save(path)
                input_paths.append(path)

            # Handle "appendReverted" logic
            if append_reverted and len(input_paths) > 1:
                # Add images in reverse order, excluding the first and last to avoid duplicates at the pivot points
                # Or simply reverse the whole list for a simpler "ping-pong"
                reversed_paths = input_paths[::-1]
                # To avoid double frames at the ends, we slice:
                # [0, 1, 2] -> [0, 1, 2, 1]
                input_paths.extend(reversed_paths[1:-1])

            output_gif_path = os.path.join(tmp_dir, "result.gif")

            # 3. Construct ImageMagick command
            # -delay is in ticks (1/100th of a second), so ms / 10
            delay_ticks = str(int(int(delay) // 10))
            
            # Command: convert -delay <ticks> -resize <size> <inputs> <output>
            cmd = [
                "convert",
                "-delay", delay_ticks,
                "-resize", target_size,
                *input_paths,
                output_gif_path
            ]

            # Execute conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({"error": f"ImageMagick error: {result.stderr}"}), 500

            # 4. Return the resulting GIF
            return send_file(output_gif_path, mimetype='image/gif')

    except ValueError:
        return jsonify({"error": "Invalid input values provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)