import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    # Validate that the file part is present in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    # Validate that a file was actually uploaded
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Ensure the file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Uploaded file must be a PDF"}), 400

    # Create a temporary directory to handle the file processing
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded PDF to the temporary directory
            file.save(input_path)

            # Use the 'pdftotext' utility from poppler-utils
            # -layout attempts to maintain the physical layout of the text
            result = subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            # Read the resulting text file
            with open(output_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()

            # Return the plain text as specified in the OpenAPI schema
            return Response(extracted_text, mimetype='text/plain')

        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Conversion failed: {e.stderr}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)