import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/create-gif', methods=['POST'])
def create_gif():
    try:
        # 1. Extract and validate inputs
        if 'images' not in request.files:
            return jsonify({"error": "Missing 'images' field"}), 400
        
        files = request.files.getlist('images')
        if not files:
            return jsonify({"error": "No images provided"}), 400

        target_size = request.form.get('targetSize')
        if not target_size:
            return jsonify({"error": "Missing 'targetSize' parameter"}), 400

        # Delay is in ms, ImageMagick uses ticks (1/100th of a second)
        # 100ms = 10 ticks.
        delay_ms = request.form.get('delay', 10)
        try:
            delay_ticks = int(delay_ms) // 10
        except ValueError:
            return jsonify({"error": "Invalid 'delay' value"}), 400

        append_reverted = request.form.get('appendReverted', 'false').lower() == 'true'

        # 2. Save uploaded files to a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file in enumerate(files):
                path = os.path.join(tmpdir, f"frame_{i}.png")
                file.save(path)
                input_paths.append(path)

            # Handle the "appendReverted" logic (Ping-pong effect)
            if append_reverted:
                # Append images in reverse order, excluding the first and last to avoid duplicates
                # if the user wants a smooth loop. However, a simple reverse is usually expected.
                # We slice [:-1] to avoid duplicating the last frame, and [:-2] to avoid duplicating the first.
                reverted_paths = input_paths[::-1]
                # To avoid double frames at the pivot points:
                if len(reverted_paths) > 1:
                    # Remove first element of reversed list because it's the same as last element of original
                    reverted_paths = reverted_paths[1:]
                    # Remove last element of reversed list because it's the same as first element of original
                    reverted_paths = reverted_paths[:-1]
                
                input_paths.extend(reverted_paths)

            output_gif_path = os.path.join(tmpdir, "result.gif")

            # 3. Construct ImageMagick command
            # convert [inputs] -resize [size] -delay [ticks] -loop 0 [output]
            cmd = [
                "convert",
                "-delay", str(delay_ticks),
                *input_paths,
                "-resize", target_size,
                "-loop", "0",
                output_gif_path
            ]

            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return jsonify({"error": f"ImageMagick error: {result.stderr}"}), 500

            # 4. Return the generated GIF
            return send_file(output_gif_path, mimetype='image/gif')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Simple HTML page for testing the API via browser
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>GIF Creator</title></head>
    <body>
        <h1>GIF Creator</h1>
        <form action="/create-gif" method="post" enctype="multipart/form-data">
            <label>Images:</label><br>
            <input type="file" name="images" multiple required><br><br>
            <label>Target Size (e.g. 500x500):</label><br>
            <input type="text" name="targetSize" placeholder="500x500" required><br><br>
            <label>Delay (ms):</label><br>
            <input type="number" name="delay" value="100"><br><br>
            <label>Append Reverted:</label>
            <input type="checkbox" name="appendReverted" value="true"><br><br>
            <input type="submit" value="Create GIF">
        </form>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)