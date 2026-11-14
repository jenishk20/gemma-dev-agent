import os
import subprocess
import tempfile
from flask import Flask, request, Response

app = Flask(__name__)

# Ensure the app handles file uploads securely
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB

@app.route('/convert', methods=['POST'])
def convert_pdf_to_text():
    """
    Converts a PDF file to plain text using the pdftotext utility.
    """
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return Response("Bad Request - Missing file", status=400, mimetype='text/plain')

    file = request.files['file']

    # Check if the user actually selected a file
    if file.filename == '':
        return Response("Bad Request - No selected file", status=400, mimetype='text/plain')

    # Validate file extension for basic security
    if not file.filename.lower().endswith('.pdf'):
        return Response("Bad Request - File must be a PDF", status=400, mimetype='text/plain')

    # Use a temporary directory to handle the file securely
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded file to the temporary path
            file.save(input_path)

            # Execute pdftotext from poppler-utils
            # -layout preserves the visual layout of the text
            result = subprocess.run(
                ['pdftotext', '-layout', input_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the generated text file
            with open(output_path, 'r', encoding='utf-8') as f:
                text_content = f.read()

            return Response(text_content, status=200, mimetype='text/plain')

        except subprocess.CalledProcessError as e:
            # Log error if necessary and return 500
            return Response(f"Internal Server Error - Conversion failed: {str(e)}", status=500, mimetype='text/plain')
        except Exception as e:
            return Response(f"Internal Server Error - {str(e)}", status=500, mimetype='text/plain')

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)