import os
import subprocess
import tempfile
from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return Response("Bad Request - Missing file", status=400, mimetype='text/plain')

    file = request.files['file']

    # Check if no file was selected
    if file.filename == '':
        return Response("Bad Request - No file selected", status=400, mimetype='text/plain')

    # Ensure the file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        return Response("Bad Request - File must be a PDF", status=400, mimetype='text/plain')

    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded PDF to the temporary directory
            file.save(input_path)

            # Use the poppler-utils 'pdftotext' command to extract text
            # pdftotext [input-pdf] [output-text-file]
            result = subprocess.run(
                ['pdftotext', input_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the extracted text from the output file
            with open(output_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()

            return Response(extracted_text, status=200, mimetype='text/plain')

        except subprocess.CalledProcessError as e:
            return Response(f"Internal Server Error - Conversion failed: {str(e)}", status=500, mimetype='text/plain')
        except Exception as e:
            return Response(f"Internal Server Error - {str(e)}", status=500, mimetype='text/plain')

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)