import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum size of the uploaded file (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    # Validate that the file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # Validate that a file was actually uploaded
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Security: Path Traversal prevention. 
    # We ignore the user-provided filename for the actual disk write to prevent 
    # path traversal attacks (e.g., filename="../../etc/passwd").
    # We only check the extension for validation.
    filename_lower = file.filename.lower()
    if not filename_lower.endswith('.pdf'):
        return jsonify({"error": "Uploaded file must be a PDF"}), 400

    # Create a temporary directory to handle the file processing
    # tempfile.TemporaryDirectory is secure and creates a unique path
    with tempfile.TemporaryDirectory() as tmpdir:
        # We use hardcoded filenames inside the secure temp directory
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded PDF. Since we use a fixed name, 
            # the user-supplied filename cannot influence the filesystem path.
            file.save(input_path)

            # Security: Shell Injection prevention.
            # subprocess.run is called with a list (shell=False by default), 
            # which avoids shell interpretation of arguments.
            # We add a timeout to prevent resource exhaustion (DoS via hanging process).
            subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=30  # Limit execution time to 30 seconds
            )

            # Read the resulting text file
            with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                extracted_text = f.read()

            # Return the plain text as specified in the OpenAPI schema
            return Response(extracted_text, mimetype='text/plain')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "Conversion timed out"}), 500
        except subprocess.CalledProcessError:
            # Error handling: Return documented error status without leaking internal stderr/stack traces
            return jsonify({"error": "Conversion failed"}), 500
        except Exception:
            # Catch-all to prevent leaking internal server details/stack traces
            return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)