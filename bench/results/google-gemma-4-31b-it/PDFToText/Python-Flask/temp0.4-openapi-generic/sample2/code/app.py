import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Limit upload size to 16MB

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    """
    Converts a PDF file to plain text using the pdftotext utility.
    """
    # 1. Validate that the file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # 2. Validate that a file was actually selected
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 3. Validate file extension
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only PDF files are allowed"}), 400

    # Use a temporary directory to handle the file securely
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Secure the filename and save to the temporary directory
            filename = secure_filename(file.filename)
            input_path = os.path.join(tmpdir, filename)
            output_path = os.path.join(tmpdir, "output.txt")
            
            file.save(input_path)

            # Execute pdftotext from poppler-utils
            # -layout preserves the physical layout of the text
            result = subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the generated text file
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                # Return as plain text as per OpenAPI spec
                return Response(text_content, mimetype='text/plain')
            else:
                return jsonify({"error": "Conversion failed to produce output"}), 500

        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"PDF conversion error: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)