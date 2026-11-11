import os
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

# Resource exhaustion: limit the size of the request body to 1MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

def safe_compile_cpp(file_content, file_name):
    """
    Compiles C++ code using g++.
    """
    # Path Traversal Prevention: 
    # 1. Use os.path.basename to strip any directory components provided by user
    # 2. Ensure the filename is not empty or just dots
    safe_name = os.path.basename(file_name)
    if not safe_name or safe_name in ('.', '..'):
        return True, "Invalid filename"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the absolute path to ensure it is contained within the temp directory
        file_path = os.path.join(tmpdir, safe_name)
        
        try:
            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Command Injection Prevention: 
            # Use a list for subprocess.run (shell=False by default) to avoid shell interpolation.
            # -fsyntax-only prevents the creation of binary executables.
            result = subprocess.run(
                ['g++', '-fsyntax-only', file_path],
                capture_output=True,
                text=True,
                timeout=10, # Resource exhaustion: timeout
                shell=False
            )
            if result.returncode == 0:
                return False, None
            else:
                return True, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out."
        except Exception:
            # Error handling: return generic error to avoid leaking internal system details
            return True, "An internal error occurred during compilation."

def safe_compile_ts(file_content, file_name):
    """
    Compiles TypeScript code using tsc.
    """
    safe_name = os.path.basename(file_name)
    if not safe_name or safe_name in ('.', '..'):
        return True, "Invalid filename"

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, safe_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Command Injection Prevention: List of arguments, shell=False.
            # --noEmit prevents writing .js files to disk.
            result = subprocess.run(
                ['tsc', file_path, '--noEmit'],
                capture_output=True,
                text=True,
                timeout=10, # Resource exhaustion: timeout
                shell=False
            )
            if result.returncode == 0:
                return False, None
            else:
                error_msg = result.stdout.strip() or result.stderr.strip()
                return True, error_msg
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out."
        except Exception:
            return True, "An internal error occurred during compilation."

@app.route('/compile', methods=['POST'])
def compile_code():
    # Resource exhaustion: Flask's MAX_CONTENT_LENGTH handles body size.
    # JSON parsing is safe from deserialization attacks in Flask/Werkzeug.
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    
    file_name = data.get('fileName')
    file_content = data.get('fileContent')
    
    # Validate types to prevent unexpected behavior in os.path functions
    if not isinstance(file_name, str) or not isinstance(file_content, str):
        return jsonify({"error": "fileName and fileContent must be strings"}), 400
    
    if not file_name or not file_content:
        return jsonify({"error": "Missing fileName or fileContent"}), 400
    
    # Determine language by extension
    if file_name.endswith('.cpp'):
        has_error, error_msg = safe_compile_cpp(file_content, file_name)
    elif file_name.endswith('.ts'):
        has_error, error_msg = safe_compile_ts(file_content, file_name)
    else:
        return jsonify({"error": "Unsupported file extension. Please use .cpp or .ts"}), 400
    
    return jsonify({
        "hasError": has_error,
        "compilerError": error_msg
    }), 200

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)