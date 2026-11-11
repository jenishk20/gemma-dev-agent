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
    # Validate that 'files' is present in the request
    if 'files' not in request.files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    uploaded_files = request.files.getlist('files')
    
    if not uploaded_files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Resource exhaustion: Limit the number of files to prevent command line length overflow
    if len(uploaded_files) > 100:
        return jsonify({"error": "Too many files provided."}), 400

    # Create a temporary directory to store the uploaded files and the result
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(uploaded_files):
                # Path Traversal Prevention: 
                # We ignore the user-provided filename entirely when saving to disk.
                # We generate our own safe filename based on the index.
                if not file.filename.lower().endswith('.pdf'):
                    return jsonify({"error": "Invalid input or missing files."}), 400
                
                # Use a strictly controlled path inside the temp directory
                safe_filename = f"input_{i}.pdf"
                file_path = os.path.join(tmpdir, safe_filename)
                
                # Double check that the resolved path is still inside tmpdir (defense in depth)
                if not os.path.abspath(file_path).startswith(os.path.abspath(tmpdir)):
                    return jsonify({"error": "Invalid input or missing files."}), 400
                
                file.save(file_path)
                input_paths.append(file_path)

            # Define the output path
            output_path = os.path.join(tmpdir, "concatenated.pdf")

            # Shell Injection Prevention:
            # We use a list for the command and shell=False (default in subprocess.run).
            # This ensures that arguments are passed directly to the execve syscall 
            # and not interpreted by a shell, preventing command injection.
            command = ['pdfunite'] + input_paths + [output_path]
            
            # Execute the CLI tool with a timeout to prevent resource exhaustion (DoS)
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                shell=False, 
                timeout=30
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