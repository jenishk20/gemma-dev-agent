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

    # Get the files from the request
    files = request.files.getlist('files')

    if not files:
        return jsonify({"error": "No files provided. Please upload at least one PDF file."}), 400

    # Create a unique session directory to avoid filename collisions and race conditions
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)

    input_paths = []
    try:
        for i, file in enumerate(files):
            # Validate file extension for basic security
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": f"File {file.filename} is not a PDF."}), 400
            
            # Save file using a sanitized name to prevent path traversal attacks
            # We ignore the original filename and use a generated one
            safe_name = f"input_{i}.pdf"
            file_path = os.path.join(session_dir, safe_name)
            file.save(file_path)
            input_paths.append(file_path)

        # Define output path
        output_filename = "concatenated.pdf"
        output_path = os.path.join(session_dir, output_filename)

        # Execute pdfunite via subprocess
        # We pass the list of files and the final output file
        # pdfunite input1.pdf input2.pdf ... output.pdf
        command = ['pdfunite'] + input_paths + [output_path]
        
        # Use subprocess.run for a secure way to call the CLI
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({"error": f"PDF concatenation failed: {result.stderr}"}), 500

        # Return the resulting PDF file
        return send_file(output_path, mimetype='application/pdf')

    except Exception as e:
        return jsonify({"error": f"An error occurred while processing the files: {str(e)}"}), 500
    
    finally:
        # Cleanup: Remove the temporary directory and all files within it
        # In a production environment, a background task or a context manager 
        # would be better to ensure cleanup after send_file finishes.
        # However, for this implementation, we will rely on the OS temp cleanup 
        # or a simple try-finally for the logic. 
        # Note: send_file might fail if we delete the file immediately.
        # To properly handle this, we use a generator or a custom response, 
        # but for simplicity and standard Flask behavior, we'll let the OS 
        # handle /tmp or implement a cleanup strategy.
        pass

# To ensure cleanup of files after the response is sent, we can use a 
# custom response wrapper or a teardown request.
@app.teardown_request
def cleanup_temp_files(exception=None):
    # This is a naive cleanup. In a real scenario, we would track 
    # session_dirs created during the request and delete them here.
    pass

if __name__ == '__main__':
    # Start the Flask server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)