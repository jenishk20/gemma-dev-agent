import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion limits
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB total request size
MAX_FILE_COUNT = 100                   # Max number of PDFs to concatenate

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    # 1. Validate request body presence
    if 'files' not in request.files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    files = request.files.getlist('files')
    
    # 2. Resource exhaustion: Bound the number of files
    if not files or len(files) == 0:
        return jsonify({"error": "Invalid input or missing files."}), 400
    
    if len(files) > MAX_FILE_COUNT:
        return jsonify({"error": "Too many files provided."}), 400

    # Use a temporary directory to isolate files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            for i, file in enumerate(files):
                # Path Traversal Prevention: 
                # We ignore the user-provided filename entirely and generate 
                # our own safe filename inside the controlled temp directory.
                if file.filename == '':
                    continue
                
                # Generate a deterministic, safe filename
                safe_filename = f"input_{i}.pdf"
                file_path = os.path.join(tmpdir, safe_filename)
                
                # Save the file content
                file.save(file_path)
                input_paths.append(file_path)

            if not input_paths:
                return jsonify({"error": "Invalid input or missing files."}), 400

            output_path = os.path.join(tmpdir, "concatenated.pdf")

            # Shell Injection Prevention:
            # We use a list for arguments and shell=False (default for subprocess.run).
            # This ensures the input paths are treated as literal arguments, not shell commands.
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute with a timeout to prevent DoS via hanging processes
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30, 
                shell=False 
            )
            
            if result.returncode != 0:
                # Error handling: Return documented 500 without leaking internal system paths
                return jsonify({"error": "An error occurred while processing the files."}), 500

            # Return the resulting PDF file
            return send_file(output_path, mimetype='application/pdf')

        except subprocess.TimeoutExpired:
            return jsonify({"error": "An error occurred while processing the files."}), 500
        except Exception:
            # Generic catch-all to prevent leaking stack traces
            return jsonify({"error": "An error occurred while processing the files."}), 500

if __name__ == '__main__':
    # Start the webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)