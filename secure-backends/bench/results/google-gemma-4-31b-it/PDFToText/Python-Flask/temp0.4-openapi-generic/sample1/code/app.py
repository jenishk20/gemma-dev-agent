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

    # Check if no file was selected
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Invalid file type. Please upload a PDF file."}), 400

    # Use a temporary directory to handle the file securely
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Secure the filename and save it to the temp directory
            filename = secure_filename(file.filename)
            input_path = os.path.join(tmpdir, filename)
            output_path = os.path.join(tmpdir, "output.txt")

            file.save(input_path)

            # Execute pdftotext utility
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
                return jsonify({"error": "Conversion failed: Output file not created"}), 500

        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"pdftotext utility error: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Start the webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)