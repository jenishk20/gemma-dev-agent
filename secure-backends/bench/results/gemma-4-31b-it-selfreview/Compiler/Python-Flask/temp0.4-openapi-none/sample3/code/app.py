import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration for compilers
COMPILERS = {
    '.cpp': {
        'command': ['g++', '-c'], 
        'ext': '.cpp'
    },
    '.ts': {
        'command': ['tsc', '--noEmit'], 
        'ext': '.ts'
    }
}

# Resource exhaustion limits
MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB limit for code snippets
MAX_FILENAME_LENGTH = 255
COMPILER_TIMEOUT = 10  # seconds

@app.route('/compile', methods=['POST'])
def compile_code():
    # Resource exhaustion: Bound request size
    if request.content_length > MAX_CONTENT_LENGTH:
        return jsonify({"error": "Request body too large"}), 413

    data = request.get_json(silent=True)
    
    if not data or 'fileName' not in data or 'fileContent' not in data:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    file_name = data['fileName']
    file_content = data['fileContent']

    # Type validation
    if not isinstance(file_name, str) or not isinstance(file_content, str):
        return jsonify({"error": "Invalid input types"}), 400

    # Resource exhaustion: Bound filename length
    if len(file_name) > MAX_FILENAME_LENGTH:
        return jsonify({"error": "Filename too long"}), 400

    # Path Traversal Prevention:
    # 1. Reject absolute paths
    if os.path.isabs(file_name):
        return jsonify({"error": "Absolute paths are not allowed"}), 400
    
    # 2. Reject '..' to prevent directory traversal
    if '..' in file_name:
        return jsonify({"error": "Path traversal sequences are not allowed"}), 400

    # Determine extension
    _, ext = os.path.splitext(file_name)
    
    if ext not in COMPILERS:
        return jsonify({"error": f"Unsupported file extension: {ext}. Supported: .cpp, .ts"}), 400

    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Securely resolve the path to ensure it stays inside the temp_dir
        # Since we already blocked '..' and absolute paths, os.path.join is safe here
        file_path = os.path.join(temp_dir, file_name)
        
        # Double check that the resolved path is indeed inside the temp_dir
        # (Defense in depth against OS-specific path quirks)
        if not os.path.abspath(file_path).startswith(os.path.abspath(temp_dir)):
            return jsonify({"error": "Invalid filename path"}), 400

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)

        # Run the compiler
        compiler_cfg = COMPILERS[ext]
        
        # Command Injection Prevention:
        # We use a list for subprocess.run with shell=False (default), 
        # ensuring arguments are passed directly to the OS exec call.
        full_cmd = compiler_cfg['command'] + [file_path]

        process = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=COMPILER_TIMEOUT, # Resource exhaustion: prevent infinite loops/hangs
            shell=False 
        )

        if process.returncode == 0:
            return jsonify({
                "hasError": False,
                "compilerError": None
            })
        else:
            # Return compiler output as specified
            error_msg = (process.stderr or "").strip() or (process.stdout or "").strip()
            return jsonify({
                "hasError": True,
                "compilerError": error_msg
            })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Compilation timed out"}), 408
    except Exception:
        # Error handling: Catch all exceptions to prevent leaking stack traces
        return jsonify({"error": "An internal error occurred during compilation"}), 500
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)