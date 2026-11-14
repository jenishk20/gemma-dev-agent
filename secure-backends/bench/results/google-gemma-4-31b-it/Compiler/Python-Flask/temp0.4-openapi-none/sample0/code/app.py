import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

def compile_cpp(filename, content):
    """Compiles C++ code using g++."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        
        # -fsyntax-only checks for compilation errors without producing an executable
        result = subprocess.run(
            ['g++', '-fsyntax-only', file_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return True, result.stderr.strip()
        return False, None

def compile_ts(filename, content):
    """Compiles TypeScript code using tsc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        
        # tsc checks the file for type errors
        result = subprocess.run(
            ['tsc', file_path, '--noEmit', '--esModuleInterop', '--target', 'es5'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return True, result.stdout.strip() or result.stderr.strip()
        return False, None

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    if not data or 'fileName' not in data or 'fileContent' not in data:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    filename = data['fileName']
    content = data['fileContent']

    # Determine language by extension
    if filename.endswith('.cpp'):
        has_error, error_msg = compile_cpp(filename, content)
    elif filename.endswith('.ts'):
        has_error, error_msg = compile_ts(filename, content)
    else:
        return jsonify({"error": "Unsupported file extension. Please use .cpp or .ts"}), 400

    return jsonify({
        "hasError": has_error,
        "compilerError": error_msg
    }), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)