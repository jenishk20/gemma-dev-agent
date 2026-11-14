import os
import subprocess
import tempfile
from flask import Flask, request, Response

app = Flask(__name__)

# Resource exhaustion: Limit the maximum allowed upload size (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return Response("Bad Request - Missing file", status=400, mimetype='text/plain')

    file = request.files['file']

    # Check if no file was selected
    if file.filename == '':
        return Response("Bad Request - No file selected", status=400, mimetype='text/plain')

    # Path Traversal Prevention: 
    # We ignore the user-provided filename entirely when saving to the filesystem.
    # We only check the extension for validation.
    filename = file.filename
    if not filename.lower().endswith('.pdf'):
        return Response("Bad Request - File must be a PDF", status=400, mimetype='text/plain')

    # Use a temporary directory to isolate files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Hardcode filenames inside the temp directory to prevent path traversal
        # and ensure untrusted input never reaches a file path.
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded PDF using the controlled path
            file.save(input_path)

            # Command Injection Prevention:
            # Use a list for arguments (shell=False by default in subprocess.run).
            # This prevents the shell from interpreting special characters in paths.
            # We also add a timeout to prevent resource exhaustion (DoS).
            subprocess.run(
                ['pdftotext', input_path, output_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Prevent hanging processes
            )

            # Read the extracted text from the output file
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                    extracted_text = f.read()
                return Response(extracted_text, status=200, mimetype='text/plain')
            else:
                return Response("Internal Server Error - Conversion failed", status=500, mimetype='text/plain')

        except subprocess.TimeoutExpired:
            return Response("Internal Server Error - Conversion timed out", status=500, mimetype='text/plain')
        except subprocess.CalledProcessError:
            # Error handling: Return documented status code without leaking internal stack traces
            return Response("Internal Server Error - Conversion failed", status=500, mimetype='text/plain')
        except Exception:
            # Catch-all for any other unexpected errors to prevent leaking internal details
            return Response("Internal Server Error - An unexpected error occurred", status=500, mimetype='text/plain')

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)