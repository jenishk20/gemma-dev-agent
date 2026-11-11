import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Resource exhaustion: Limit the maximum upload size to 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    """
    Convert a PDF file to Text using the pdftotext utility.
    """
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # Check if a file was actually uploaded
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Path Traversal Prevention: 
    # secure_filename removes directory separators and '..' to prevent path traversal.
    filename = secure_filename(file.filename)
    
    # Ensure the file is a PDF based on the sanitized filename
    if not filename.lower().endswith('.pdf'):
        return jsonify({"error": "Uploaded file must be a PDF"}), 400

    # Create a temporary directory to handle the file processing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve paths to ensure they are absolute and contained within tmpdir
        input_path = os.path.abspath(os.path.join(tmpdir, filename))
        output_path = os.path.abspath(os.path.join(tmpdir, "output.txt"))

        # Double check that the resolved path is still inside the tmpdir
        if not input_path.startswith(os.path.abspath(tmpdir)):
            return jsonify({"error": "Invalid file path"}), 400

        try:
            # Save the uploaded file to the temporary path
            file.save(input_path)

            # Command Injection Prevention:
            # We use a list for arguments and shell=False (default) to avoid shell interpretation.
            # We also add a timeout to prevent resource exhaustion (DoS) via hanging processes.
            subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=30 
            )

            # Read the generated text file
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                    extracted_text = f.read()
                # Return the extracted text as plain text
                return Response(extracted_text, mimetype='text/plain')
            else:
                return jsonify({"error": "Conversion failed to produce output"}), 500

        except subprocess.TimeoutExpired:
            return jsonify({"error": "Conversion timed out"}), 500
        except subprocess.CalledProcessError:
            # Error handling: Do not leak stderr to the client to avoid leaking internal system details
            return jsonify({"error": "Conversion failed"}), 500
        except Exception:
            # Generic catch-all to prevent leaking stack traces
            return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    # Run the server on port 5000, accessible from all interfaces
    app.run(host='0.0.0.0', port=5000)