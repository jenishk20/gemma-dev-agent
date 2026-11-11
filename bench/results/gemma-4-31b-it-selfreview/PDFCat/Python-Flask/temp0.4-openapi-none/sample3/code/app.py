import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum size of the request body (e.g., 50MB)
# This prevents attackers from crashing the server with massive uploads.
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    # Check if 'files' key exists in the request
    if 'files' not in request.files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    files = request.files.getlist('files')
    
    if not files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Resource exhaustion: Limit the number of files to prevent command line length overflow
    if len(files) > 100:
        return jsonify({"error": "Too many files provided."}), 400

    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(files):
                # Security: We ignore the user-provided filename entirely to prevent 
                # path traversal attacks. We generate our own safe filename.
                # We only check the extension for basic validation.
                filename = file.filename
                if not filename or not filename.lower().endswith('.pdf'):
                    return jsonify({"error": "All uploaded files must be PDFs."}), 400
                
                # Use a fixed, safe naming convention inside the temp directory
                safe_name = f"input_{i}.pdf"
                file_path = os.path.join(tmpdir, safe_name)
                
                # Save the file stream to the safe path
                file.save(file_path)
                input_paths.append(file_path)

            # Define the output path
            output_path = os.path.join(tmpdir, "concatenated.pdf")

            # Security: Untrusted input reaching a shell.
            # We use a list for subprocess.run with shell=False (default).
            # This ensures that arguments are passed directly to the execve system call,
            # preventing shell injection.
            command = ['pdfunite'] + input_paths + [output_path]
            
            # Run the command with a timeout to prevent resource exhaustion (DoS)
            # and capture_output to prevent leaking internal shell details to the user.
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30,
                shell=False 
            )
            
            if result.returncode != 0:
                # Error handling: Return generic error message as per OpenAPI spec 
                # to avoid leaking internal system paths or poppler-utils errors.
                return jsonify({"error": "An error occurred while processing the files."}), 500

            # Return the concatenated PDF file
            return send_file(output_path, mimetype='application/pdf')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "An error occurred while processing the files."}), 500
        except Exception:
            # Error handling: Catch all exceptions and return the documented 500 error
            # without leaking stack traces or internal details.
            return jsonify({"error": "An error occurred while processing the files."}), 500

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)