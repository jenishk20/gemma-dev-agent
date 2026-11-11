import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum size of the request body (e.g., 50MB)
# This prevents memory exhaustion from massive uploads.
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    # Check if 'files' key exists in the multipart request
    if 'files' not in request.files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    files = request.files.getlist('files')
    
    if not files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Resource exhaustion: Limit the number of files to prevent OS command line length limits 
    # and disk space exhaustion.
    if len(files) > 100:
        return jsonify({"error": "Too many files provided."}), 400

    # Create a temporary directory to store uploaded files and the result
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(files):
                # Security: Ignore the user-provided filename for the actual disk write
                # to prevent path traversal attacks. We use a generated index.
                # We only check the extension for basic validation.
                filename = file.filename if file.filename else "unknown"
                if not filename.lower().endswith('.pdf'):
                    return jsonify({"error": "Invalid input or missing files."}), 400
                
                # Use a safe, controlled path inside the temporary directory
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                file.save(file_path)
                input_paths.append(file_path)

            output_path = os.path.join(tmpdir, "concatenated.pdf")
            
            # Security: Use a list for subprocess.run to avoid shell injection.
            # shell=False is the default, ensuring arguments are passed directly to the exec syscall.
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute the CLI tool with a timeout to prevent DoS via hanging processes
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30, 
                shell=False
            )
            
            if result.returncode != 0:
                # Error handling: Return the documented error status code without leaking 
                # internal system paths or detailed stderr to the client.
                return jsonify({"error": "An error occurred while processing the files."}), 500

            # Return the resulting PDF file
            return send_file(output_path, mimetype='application/pdf')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "An error occurred while processing the files."}), 500
        except Exception:
            # Error handling: Catch all exceptions to prevent leaking stack traces
            return jsonify({"error": "An error occurred while processing the files."}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)