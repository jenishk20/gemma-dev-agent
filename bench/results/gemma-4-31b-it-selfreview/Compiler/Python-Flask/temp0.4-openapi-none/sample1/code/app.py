import os
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration for compilers
COMPILERS = {
    '.cpp': {
        'command': 'g++',
        'args': ['-std=c++17', '-Wall'],
    },
    '.ts': {
        'command': 'tsc',
        'args': ['--noEmit', '--target', 'es5'],
    }
}

# Resource exhaustion limits
MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB limit for code content
MAX_FILENAME_LENGTH = 255

@app.route('/compile', methods=['POST'])
def compile_code():
    # Resource exhaustion: bound request size
    if request.content_length > MAX_CONTENT_LENGTH:
        return jsonify({"error": "Request body too large"}), 413

    data = request.get_json(silent=True)
    
    if not data or 'fileName' not in data or 'fileContent' not in data:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    file_name = data['fileName']
    file_content = data['fileContent']

    # Validate input types to prevent unexpected behavior in string operations
    if not isinstance(file_name, str) or not isinstance(file_content, str):
        return jsonify({"error": "Invalid input types"}), 400

    # Resource exhaustion: bound filename length
    if len(file_name) > MAX_FILENAME_LENGTH:
        return jsonify({"error": "Filename too long"}), 400

    # Path Traversal Prevention:
    # 1. Reject absolute paths
    if os.path.isabs(file_name):
        return jsonify({"error": "Absolute paths are not allowed"}), 400
    
    # 2. Reject directory traversal attempts ('..')
    if '..' in file_name or '/' in file_name or '\\' in file_name:
        return jsonify({"error": "Invalid characters in filename"}), 400

    # Determine language by extension
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()

    if ext not in COMPILERS:
        return jsonify({"error": f"Unsupported file extension: {ext}"}), 400

    config = COMPILERS[ext]
    
    # Use a secure temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the final path and ensure it is strictly within the tmpdir
        # Since we already stripped '..' and '/', this is a secondary safety layer
        file_path = os.path.join(tmpdir, file_name)
        if not os.path.commonprefix([os.path.abspath(file_path), os.path.abspath(tmpdir)]) == os.path.abspath(tmpdir):
            return jsonify({"error": "Invalid file path"}), 400
        
        try:
            # Write content safely
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Command Injection Prevention:
            # We use a list for subprocess.run with shell=False (default), 
            # which avoids the shell and treats arguments as literal strings.
            cmd = [config['command']] + config['args']
            
            if ext == '.cpp':
                # Ensure output file is also inside the secure tmpdir
                out_path = os.path.join(tmpdir, 'out.bin')
                cmd += [file_path, '-o', out_path]
            else:
                cmd += [file_path]

            # Resource exhaustion: timeout prevents hanging processes
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10,
                shell=False 
            )

            if process.returncode == 0:
                return jsonify({
                    "hasError": False,
                    "compilerError": None
                })
            else:
                # Return the compiler output. Since this is returned as JSON, 
                # Flask/jsonify handles the escaping to prevent XSS/Injection.
                error_msg = process.stderr.strip() or process.stdout.strip()
                return jsonify({
                    "hasError": True,
                    "compilerError": error_msg if error_msg else "Unknown compilation error"
                })

        except subprocess.TimeoutExpired:
            return jsonify({
                "hasError": True,
                "compilerError": "Compilation timed out"
            })
        except Exception:
            # Error handling: return a generic error to avoid leaking internal stack traces
            return jsonify({
                "hasError": True,
                "compilerError": "An internal error occurred during compilation"
            })

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)