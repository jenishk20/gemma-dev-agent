import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the size of the request body to prevent DoS
# 16MB limit for the total request size
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/create-gif', methods=['POST'])
def create_gif():
    try:
        # 1. Extract and validate inputs
        if 'images' not in request.files:
            return jsonify({"error": "Missing 'images' field"}), 400
        
        files = request.files.getlist('images')
        if not files:
            return jsonify({"error": "No images provided"}), 400

        # Resource exhaustion: Limit the number of images to prevent CPU/Memory exhaustion
        if len(files) > 100:
            return jsonify({"error": "Too many images provided (max 100)"}), 400

        target_size = request.form.get('targetSize')
        if not target_size:
            return jsonify({"error": "Missing 'targetSize' parameter"}), 400

        # Security: Validate targetSize format to prevent command injection or ImageMagick exploits
        # Expected format: widthxheight (e.g., 500x500)
        import re
        if not re.match(r'^\d+x\d+$', target_size):
            return jsonify({"error": "Invalid targetSize format. Expected widthxheight (e.g. 500x500)"}), 400

        delay_ms = request.form.get('delay', '10')
        try:
            delay_ticks = int(delay_ms) // 10
            if delay_ticks < 0:
                raise ValueError()
        except ValueError:
            return jsonify({"error": "Invalid 'delay' value"}), 400

        append_reverted = request.form.get('appendReverted', 'false').lower() == 'true'

        # 2. Save uploaded files to a temporary directory
        # tempfile.TemporaryDirectory is secure and prevents path traversal
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file in enumerate(files):
                # Security: We ignore the original filename provided by the client
                # and generate our own safe filename to prevent path traversal.
                safe_filename = f"frame_{i}.png"
                path = os.path.join(tmpdir, safe_filename)
                file.save(path)
                input_paths.append(path)

            if append_reverted:
                reverted_paths = input_paths[::-1]
                if len(reverted_paths) > 1:
                    reverted_paths = reverted_paths[1:-1]
                input_paths.extend(reverted_paths)

            output_gif_path = os.path.join(tmpdir, "result.gif")

            # 3. Construct ImageMagick command
            # Security: Use a list for subprocess.run to avoid shell=True (prevents shell injection)
            # All inputs passed to the list are treated as arguments, not shell commands.
            cmd = [
                "convert",
                "-delay", str(delay_ticks),
                *input_paths,
                "-resize", target_size,
                "-loop", "0",
                output_gif_path
            ]

            # Security: Add a timeout to prevent resource exhaustion (hanging processes)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                # Error handling: Return 500 but avoid leaking internal system paths or stack traces
                return jsonify({"error": "Internal server error during image processing"}), 500

            # 4. Return the generated GIF
            return send_file(output_gif_path, mimetype='image/gif')

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Image processing timed out"}), 500
    except Exception:
        # Error handling: Catch all unexpected exceptions and return a generic 500 error
        # to prevent leaking internal details/stack traces.
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/')
def index():
    # Security: The HTML is static and contains no user-supplied input, so no XSS risk here.
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>GIF Creator</title></head>
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
    # Start webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)