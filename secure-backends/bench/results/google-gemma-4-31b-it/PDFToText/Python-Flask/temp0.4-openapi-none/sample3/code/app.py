import os
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

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

    # Validate that the file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Uploaded file must be a PDF"}), 400

    # Create a temporary directory to handle the file processing
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded file to the temporary path
            file.save(input_path)

            # Execute the pdftotext utility from poppler-utils
            # -layout attempts to maintain the physical layout of the text
            result = subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the resulting text file
            with open(output_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()

            # Return the text as plain text as per OpenAPI spec
            return Response(extracted_text, mimetype='text/plain')

        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Conversion failed: {e.stderr or str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)