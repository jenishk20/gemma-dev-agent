import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration for compilers
COMPILERS = {
    '.cpp': {
        'command': ['g++', '-'],
        'args': ['-x', 'c++', '-'], # Treat stdin as C++
        'extension': '.cpp'
    },
    '.ts': {
        'command': ['tsc'],
        'args': ['--noEmit', '--esModuleInterop'], # Check for errors without outputting files
        'extension': '.ts'
    }
}

def run_compiler(filename, content):
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in COMPILERS:
        return True, "Unsupported file extension."

    # Use a temporary directory to avoid clutter and potential collisions
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        
        # Security: Prevent directory traversal by using only the basename of the filename
        safe_filename = os.path.basename(filename)
        secure_path = os.path.join(tmpdir, safe_filename)
        
        try:
            with open(secure_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            if ext == '.cpp':
                # For C++, we compile the file. 
                # We use -K (if available) or just standard g++
                # We redirect stderr to capture compiler errors
                process = subprocess.run(
                    ['g++', secure_path, '-o', os.path.join(tmpdir, 'out')],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            elif ext == '.ts':
                # For TypeScript, we use tsc. 
                # tsc usually expects a file path.
                process = subprocess.run(
                    ['tsc', secure_path, '--noEmit'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            if process.returncode != 0:
                # Return the stderr as the compiler error
                return False, process.stderr.strip() or process.stdout.strip()
            else:
                return True, None
                
        except subprocess.TimeoutExpired:
            return False, "Compilation timed out."
        except Exception as e:
            return False, str(e)

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    
    file_name = data.get('fileName')
    file_content = data.get('fileContent')
    
    if not file_name or file_content is None:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    # Basic validation to prevent extremely large inputs
    if len(file_content) > 100000: # 100KB limit
        return jsonify({"error": "Code content too large"}), 400

    success, error_msg = run_compiler(file_name, file_content)
    
    return jsonify({
        "hasError": not success,
        "compilerError": error_msg if not success else None
    }), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)