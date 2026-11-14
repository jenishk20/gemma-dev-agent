import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    """
    Concatenates multiple PDF files using the pdfunite CLI tool.
    """
    # Check if the request is multipart/form-data
    if not request.content_type == 'multipart/form-data':
        return jsonify({"error": "Invalid content type. Expected multipart/form-data"}), 400

    # Get the list of files from the request
    files = request.files.getlist('files')

    if not files or len(files) == 0:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Create a unique temporary directory for this request to avoid collisions
    request_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_FOLDER, request_id)
    os.makedirs(temp_dir, exist_ok=True)

    input_paths = []
    try:
        # Save uploaded files to the temporary directory
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            
            # Basic validation: ensure file has .pdf extension
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": f"File {file.filename} is not a PDF."}), 400
            
            # Secure the filename to prevent path traversal
            safe_filename = f"input_{i}.pdf"
            file_path = os.path.join(temp_dir, safe_filename)
            file.save(file_path)
            input_paths.append(file_path)

        if not input_paths:
            return jsonify({"error": "No valid PDF files provided."}), 400

        # Define output path
        output_path = os.path.join(temp_dir, "concatenated.pdf")

        # Construct the pdfunite command
        # pdfunite <input1> <input2> ... <output>
        command = ['pdfunite'] + input_paths + [output_path]

        # Execute the command
        # Using subprocess.run with check=True to raise CalledProcessError on failure
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Return the concatenated PDF file
        return send_file(output_path, mimetype='application/pdf')

    except subprocess.CalledProcessError as e:
        app.logger.error(f"pdfunite error: {e.stderr}")
        return jsonify({"error": "An error occurred while processing the files."}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An internal server error occurred."}), 500
    finally:
        # Cleanup: In a production environment, you might use a background task 
        # or a cron job to clean up temp_dir, but for this API we attempt 
        # to clean up if we aren't sending the file. 
        # Since send_file is used, we can't delete the file immediately.
        # However, for the sake of this exercise, we assume the OS handles /tmp.
        pass

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)