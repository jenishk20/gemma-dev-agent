import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    """
    Concatenates multiple PDF files uploaded via multipart/form-data.
    Uses the 'pdfunite' CLI tool from poppler-utils.
    """
    # Validate that the request is multipart/form-data
    if not request.content_type == 'multipart/form-data':
        return jsonify({"error": "Invalid content type. Expected multipart/form-data"}), 400

    # Get the list of files from the request
    files = request.files.getlist('files')

    if not files or len(files) == 0:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Create a temporary directory to store uploaded files and the result
    # This prevents filename collisions and ensures cleanup
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        
        try:
            for file in files:
                # Validate that the file is actually a PDF based on filename
                if not file.filename.lower().endswith('.pdf'):
                    return jsonify({"error": f"File {file.filename} is not a PDF."}), 400
                
                # Secure the filename to prevent path traversal attacks
                # We generate a unique name to avoid overwriting files with the same name
                safe_name = f"{uuid.uuid4()}.pdf"
                file_path = os.path.join(tmpdir, safe_name)
                file.save(file_path)
                input_paths.append(file_path)

            # Define the output path
            output_path = os.path.join(tmpdir, "concatenated_result.pdf")

            # Construct the command for pdfunite
            # pdfunite input1.pdf input2.pdf ... output.pdf
            command = ['pdfunite'] + input_paths + [output_path]

            # Execute the CLI command
            # We use a list for the command to avoid shell injection vulnerabilities
            result = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )

            # Return the resulting PDF file
            return send_file(
                output_path, 
                mimetype='application/pdf', 
                as_attachment=True, 
                download_name="concatenated.pdf"
            )

        except subprocess.CalledProcessError as e:
            # Log the error internally if needed
            return jsonify({"error": "An error occurred while processing the files."}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)