import os
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration for compilers
COMPILERS = {
    '.cpp': {
        'command': 'g++',
        'args': ['-c'], 
    },
    '.ts': {
        'command': 'tsc',
        'args': ['--noEmit', '--esModuleInterop'], 
    }
}

# Limit request body size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

@app.route('/compile', methods=['POST'])
def compile_code():
    # Ensure request is JSON
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    file_name = data.get('fileName')
    file_content = data.get('fileContent')

    if not isinstance(file_name, str) or not isinstance(file_content, str):
        return jsonify({"error": "fileName and fileContent must be strings"}), 400

    # Path Traversal Prevention:
    # 1. Reject absolute paths
    if os.path.isabs(file_name):
        return jsonify({"error": "Absolute paths are not allowed"}), 400
    
    # 2. Reject paths containing '..' to prevent directory traversal
    if '..' in file_name:
        return jsonify({"error": "Directory traversal is not allowed"}), 400

    # Determine language by extension
    ext = os.path.splitext(file_name)[1]
    if ext not in COMPILERS:
        return jsonify({"error": f"Unsupported file extension: {ext}"}), 400

    # Create a temporary directory to isolate execution
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the final path and verify it is still within the tmpdir
        # This is a secondary check against path traversal
        base_path = os.path.realpath(tmpdir)
        file_path = os.path.realpath(os.path.join(tmpdir, file_name))
        
        if not file_path.startswith(base_path):
            return jsonify({"error": "Invalid file path"}), 400
        
        try:
            # Write content to file safely
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
        except Exception:
            # Generic error to avoid leaking internal system details
            return jsonify({"hasError": True, "compilerError": "Failed to write source file"}), 500

        config = COMPILERS[ext]
        
        # Command Injection Prevention:
        # Use a list for subprocess.run with shell=False (default)
        # This ensures arguments are passed directly to the execve system call
        cmd = [config['command']] + config['args'] + [file_path]

        try:
            # Resource Exhaustion Prevention:
            # - timeout: prevents hanging processes
            # - stderr/stdout captured to prevent buffer overflow/blocking
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                shell=False # Explicitly disable shell
            )

            # Capture output. g++ uses stderr for errors, tsc uses stdout/stderr.
            error_output = process.stderr if process.stderr else process.stdout
            
            if process.returncode != 0:
                return jsonify({
                    "hasError": True,
                    "compilerError": error_output.strip() if error_output else "Compilation failed."
                })
            else:
                return jsonify({
                    "hasError": False,
                    "compilerError": None
                })

        except subprocess.TimeoutExpired:
            return jsonify({"hasError": True, "compilerError": "Compilation timed out."})
        except Exception:
            # Catch-all to prevent leaking stack traces
            return jsonify({"hasError": True, "compilerError": "An internal error occurred during compilation."})

if __name__ == '__main__':
    # Run on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)