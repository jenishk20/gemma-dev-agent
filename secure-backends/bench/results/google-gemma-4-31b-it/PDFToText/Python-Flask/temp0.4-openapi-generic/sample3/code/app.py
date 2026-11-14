import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Limit upload size to 16MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    """
    Converts a PDF file to plain text using the pdftotext utility.
    """
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # If user does not select file, cause an empty file submission
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Validate file extension for basic security
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Invalid file format. Please upload a PDF file."}), 400

    # Use secure_filename to prevent directory traversal attacks
    filename = secure_filename(file.filename)

    # Use a temporary directory to handle the file processing
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded PDF to the temporary directory
            file.save(input_path)

            # Execute pdftotext utility
            # -layout attempts to maintain the visual layout of the text
            result = subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the generated text file
            with open(output_path, 'r', encoding='utf-8') as f:
                text_content = f.read()

            # Return the content as plain text as per OpenAPI spec
            return Response(text_content, mimetype='text/plain')

        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Conversion failed: {e.stderr}"}), 500
        except Exception as e:
            return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)