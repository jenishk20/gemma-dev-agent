import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

def compile_cpp(file_content, file_name):
    """
    Compiles C++ code using g++.
    Returns (hasError, compilerError)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)
        
        # Run g++ compilation
        # -fsyntax-only checks for compilation errors without producing an executable
        try:
            result = subprocess.run(
                ['g++', '-fsyntax-only', file_path],
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

def compile_ts(file_content, file_name):
    """
    Compiles TypeScript code using tsc.
    Returns (hasError, compilerError)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)
        
        # Run tsc (TypeScript Compiler)
        # --noEmit ensures no js files are written to disk
        try:
            result = subprocess.run(
                ['tsc', file_path, '--noEmit'],
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
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    
    file_name = data.get('fileName')
    file_content = data.get('fileContent')
    
    if not file_name or file_content is None:
        return jsonify({"error": "Missing fileName or fileContent"}), 400
    
    # Determine language by extension
    if file_name.endswith('.cpp'):
        has_error, error_msg = compile_cpp(file_content, file_name)
    elif file_name.endswith('.ts'):
        has_error, error_msg = compile_ts(file_content, file_name)
    else:
        return jsonify({"error": "Unsupported file extension. Please use .cpp or .ts"}), 400
    
    return jsonify({
        "hasError": has_error,
        "compilerError": error_msg
    }), 200

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)