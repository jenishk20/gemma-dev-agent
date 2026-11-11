import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum allowed upload size (e.g., 16MB)
# This prevents Denial of Service via massive file uploads.
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    """
    Upload a PDF file to convert it into Text format using the pdftotext utility.
    """
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # Check if a file was actually uploaded
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Path Traversal Prevention: 
    # We do not use the user-provided filename to create paths on the server.
    # We use a hardcoded filename within a secure temporary directory.
    # This completely mitigates path traversal attacks.
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Uploaded file must be a PDF"}), 400

    # Create a temporary directory to handle the file processing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use fixed names inside the temp directory to avoid any input reaching file paths
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded file to the temporary path
            file.save(input_path)

            # Command Injection Prevention:
            # We use a list for the arguments in subprocess.run.
            # shell=False (default) ensures that the arguments are passed directly 
            # to the execvp system call, preventing shell injection.
            # We also add a timeout to prevent resource exhaustion (hanging processes).
            subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Prevent CPU/Process exhaustion
            )

            # Read the resulting text file
            with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                extracted_text = f.read()

            # Return the text as plain text as per OpenAPI spec
            return Response(extracted_text, mimetype='text/plain')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "Conversion timed out"}), 500
        except subprocess.CalledProcessError:
            # Error handling: Return generic error message to avoid leaking 
            # internal system details or stderr output to the user.
            return jsonify({"error": "Conversion failed"}), 500
        except Exception:
            # Catch-all for other unexpected errors to prevent leaking stack traces
            return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)