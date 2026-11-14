import os
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit request body size to 1MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

def safe_compile_cpp(filename, content):
    """Compiles C++ code using g++ with security constraints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Path Traversal Prevention: 
        # 1. Use os.path.basename to strip any directory components from the user-provided filename.
        # 2. Join with a secure temporary directory.
        safe_name = os.path.basename(filename)
        file_path = os.path.join(tmpdir, safe_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        try:
            # Shell Injection Prevention: 
            # Use a list of arguments and shell=False (default) to avoid shell interpretation.
            # Resource Exhaustion: Added a timeout to prevent hanging the server.
            result = subprocess.run(
                ['g++', '-fsyntax-only', file_path],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False
            )
            
            if result.returncode != 0:
                return True, result.stderr.strip()
            return False, None
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out."
        except Exception as e:
            # Error Handling: Prevent leaking internal stack traces
            return True, "Internal compiler error occurred."

def safe_compile_ts(filename, content):
    """Compiles TypeScript code using tsc with security constraints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Path Traversal Prevention
        safe_name = os.path.basename(filename)
        file_path = os.path.join(tmpdir, safe_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        try:
            # Shell Injection Prevention: Use argument list and shell=False.
            # Resource Exhaustion: Added a timeout.
            result = subprocess.run(
                ['tsc', file_path, '--noEmit', '--esModuleInterop', '--target', 'es5'],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False
            )
            
            if result.returncode != 0:
                return True, (result.stdout.strip() or result.stderr.strip())
            return False, None
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out."
        except Exception as e:
            return True, "Internal compiler error occurred."

@app.route('/compile', methods=['POST'])
def compile_code():
    try:
        # Resource exhaustion: Flask handles MAX_CONTENT_LENGTH, but we check for JSON validity
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
            
        if 'fileName' not in data or 'fileContent' not in data:
            return jsonify({"error": "Missing fileName or fileContent"}), 400

        filename = data['fileName']
        content = data['fileContent']

        # Validate input types to prevent crashes/unexpected behavior
        if not isinstance(filename, str) or not isinstance(content, str):
            return jsonify({"error": "fileName and fileContent must be strings"}), 400

        # Determine language by extension
        if filename.endswith('.cpp'):
            has_error, error_msg = safe_compile_cpp(filename, content)
        elif filename.endswith('.ts'):
            has_error, error_msg = safe_compile_ts(filename, content)
        else:
            return jsonify({"error": "Unsupported file extension. Please use .cpp or .ts"}), 400

        return jsonify({
            "hasError": has_error,
            "compilerError": error_msg
        }), 200
    except Exception:
        # Error Handling: Generic response to avoid leaking internal details
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)