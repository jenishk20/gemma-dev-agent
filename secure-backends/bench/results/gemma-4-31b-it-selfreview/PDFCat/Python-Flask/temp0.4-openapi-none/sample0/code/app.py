import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum size of the request body (e.g., 50MB)
# This prevents Denial of Service attacks via massive file uploads.
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    # Validate that 'files' is present in the request
    if 'files' not in request.files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    uploaded_files = request.files.getlist('files')
    
    # Resource exhaustion: Limit the number of files to be concatenated (e.g., 100 files)
    if not uploaded_files or len(uploaded_files) > 100:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Create a temporary directory to store the PDF fragments
    # tempfile.TemporaryDirectory is secure as it creates a private directory with restricted permissions
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(uploaded_files):
                # Security: We ignore the user-provided filename entirely to prevent Path Traversal.
                # We generate our own unique, safe filename.
                if not file.filename.lower().endswith('.pdf'):
                    return jsonify({"error": "Invalid input or missing files."}), 400
                
                # Use a UUID to ensure the filename is unpredictable and unique
                safe_filename = f"input_{i}_{uuid.uuid4().hex}.pdf"
                filepath = os.path.join(tmpdir, safe_filename)
                
                # Save the file content
                file.save(filepath)
                input_paths.append(filepath)

            # Define the output path for the concatenated PDF
            output_filename = f"concatenated_{uuid.uuid4().hex}.pdf"
            output_path = os.path.join(tmpdir, output_filename)

            # Untrusted input reaching a shell: 
            # We use a list of arguments with subprocess.run and shell=False (default).
            # This prevents shell injection because the arguments are passed directly to the exec system call.
            command = ['pdfunite'] + input_paths + [output_path]
            
            # Execute the CLI tool with a timeout to prevent resource exhaustion (hanging processes)
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                shell=False, 
                timeout=30
            )
            
            if result.returncode != 0:
                # Error handling: Return a generic error message to avoid leaking internal system details/paths
                return jsonify({"error": "An error occurred while processing the files."}), 500

            # Return the resulting PDF file
            return send_file(output_path, mimetype='application/pdf')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "An error occurred while processing the files."}), 500
        except Exception:
            # Error handling: Catch all exceptions and return the documented 500 error without stack traces
            return jsonify({"error": "An error occurred while processing the files."}), 500

if __name__ == '__main__':
    # Start the webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)