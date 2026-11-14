import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# Resource Exhaustion: Limit the maximum upload size to 16MB to prevent DoS
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # Check if a file was actually selected
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Validate that the file is a PDF based on extension
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Uploaded file must be a PDF"}), 400

    # Use a temporary directory to handle the file processing
    # This prevents path traversal as we ignore the user-provided filename 
    # and write to a system-generated secure temporary path.
    with tempfile.TemporaryDirectory() as tmpdir:
        # We use hardcoded filenames inside the secure tmpdir to avoid 
        # any untrusted input reaching the file system paths.
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded file to the temporary path
            file.save(input_path)

            # Untrusted input reaching a shell: 
            # We use a list for arguments and shell=False (default) to prevent shell injection.
            # We also implement a timeout to prevent resource exhaustion (hanging processes).
            subprocess.run(
                ['pdftotext', input_path, output_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Prevent long-running processes from consuming CPU/RAM
            )

            # Read the resulting text file
            # We specify encoding to ensure consistent behavior
            with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                extracted_text = f.read()

            # Return the text as plain text as per OpenAPI spec
            return Response(extracted_text, mimetype='text/plain')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "Conversion timed out"}), 500
        except subprocess.CalledProcessError:
            # Error handling: return documented status code without leaking internal stderr/stack trace
            return jsonify({"error": "Conversion failed"}), 500
        except Exception:
            # Catch-all for other exceptions to prevent leaking internal server details
            return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)