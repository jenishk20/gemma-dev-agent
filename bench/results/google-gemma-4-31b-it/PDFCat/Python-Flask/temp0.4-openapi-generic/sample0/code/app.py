import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    """
    Concatenates multiple PDF files using the pdfunite CLI tool.
    """
    # Validate that the request is multipart/form-data
    if not request.content_type == 'multipart/form-data':
        return jsonify({"error": "Invalid content type. Expected multipart/form-data"}), 400

    # Get the files from the request
    files = request.files.getlist('files')

    if not files or len(files) == 0:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Create a temporary directory to handle files securely
    # This prevents filename collisions and provides a clean workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            for file in files:
                # Validate file extension/type (basic check)
                if not file.filename.lower().endswith('.pdf'):
                    return jsonify({"error": f"File {file.filename} is not a PDF."}), 400
                
                # Use a UUID for the filename to prevent path traversal or overwriting
                safe_filename = f"{uuid.uuid4()}.pdf"
                file_path = os.path.join(tmpdir, safe_filename)
                file.save(file_path)
                input_paths.append(file_path)

            # Define the output path
            output_filename = f"concatenated_{uuid.uuid4()}.pdf"
            output_path = os.path.join(tmpdir, output_filename)

            # Construct the pdfunite command
            # pdfunite [input_files] [output_file]
            command = ['pdfunite'] + input_paths + [output_path]

            # Execute the CLI tool
            # shell=False is used to prevent shell injection vulnerabilities
            result = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )

            # Return the concatenated PDF file
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
    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)