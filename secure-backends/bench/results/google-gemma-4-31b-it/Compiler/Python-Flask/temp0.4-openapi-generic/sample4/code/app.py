import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

# Security configuration: limit the allowed extensions to prevent arbitrary file execution
ALLOWED_EXTENSIONS = {'.ts', '.cpp'}

def compile_cpp(filename, content):
    """Compiles C++ code using g++."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        
        # -fsanitize=undefined or other flags could be added, but for basic compilation check:
        # We use -c to only compile (not link) to avoid needing a main() function for every snippet
        # or we just try a full build. Given the schema example "void main()", we'll try full build.
        try:
            result = subprocess.run(
                ['g++', file_path, '-o', os.path.join(tmpdir, 'out')],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return False, None
            else:
                return True, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out."
        except Exception as e:
            return True, str(e)

def compile_ts(filename, content):
    """Compiles TypeScript code using tsc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        
        try:
            # tsc returns 0 on success, non-zero on error.
            # --noEmit prevents writing .js files to disk.
            # --target es5 ensures a basic compilation target.
            result = subprocess.run(
                ['tsc', file_path, '--noEmit', '--target', 'es5'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return False, None
            else:
                # tsc outputs errors to stdout usually
                error_msg = result.stdout.strip() or result.stderr.strip()
                return True, error_msg
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out."
        except Exception as e:
            return True, str(e)

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    
    if not data or 'fileName' not in data or 'fileContent' not in data:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    file_name = data['fileName']
    file_content = data['fileContent']

    # Basic validation of filename to prevent path traversal
    # Only allow the base name of the file
    safe_file_name = os.path.basename(file_name)
    
    # Determine language by extension
    _, ext = os.path.splitext(safe_file_name)
    
    if ext == '.cpp':
        has_error, error_msg = compile_cpp(safe_file_name, file_content)
    elif ext == '.ts':
        has_error, error_msg = compile_ts(safe_file_name, file_content)
    else:
        return jsonify({"error": "Unsupported file extension. Please use .ts or .cpp"}), 400

    return jsonify({
        "hasError": has_error,
        "compilerError": error_msg
    }), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)