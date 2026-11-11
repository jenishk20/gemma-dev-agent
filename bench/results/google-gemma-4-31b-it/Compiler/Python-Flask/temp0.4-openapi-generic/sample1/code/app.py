import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

# Security configuration: Define allowed extensions and a timeout for compiler processes
ALLOWED_EXTENSIONS = {'.ts', '.cpp'}
COMPILER_TIMEOUT = 10  # seconds

def get_compiler_command(file_path):
    """
    Returns the command to run based on the file extension.
    """
    ext = os.path.splitext(file_path)[1]
    if ext == '.ts':
        # tsc returns 0 on success, non-zero on error. 
        # --noEmit prevents generating .js files in the temp directory.
        return ['tsc', file_path, '--noEmit']
    elif ext == '.cpp':
        # g++ returns 0 on success. -fsyntax-only checks for compilation errors without producing an executable.
        return ['g++', '-fsyntax-only', file_path]
    return None

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    
    if not data or 'fileName' not in data or 'fileContent' not in data:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    file_name = data['fileName']
    file_content = data['fileContent']

    # Validate file extension for security and functionality
    _, ext = os.path.splitext(file_name)
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file extension. Only .ts and .cpp are allowed."}), 400

    # Use a temporary directory to avoid polluting the filesystem and prevent path traversal attacks
    with tempfile.TemporaryDirectory() as tmpdir:
        # Ensure the filename is just a name, not a path
        safe_name = os.path.basename(file_name)
        file_path = os.path.join(tmpdir, safe_name)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
        except Exception as e:
            return jsonify({"error": f"Failed to write file: {str(e)}"}), 500

        cmd = get_compiler_command(file_path)
        if not cmd:
            return jsonify({"error": "Compiler not configured for this extension"}), 500

        try:
            # Run the compiler process. 
            # capture_output=True captures stdout and stderr.
            # timeout prevents Denial of Service via infinite loops or heavy compilation.
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=COMPILER_TIMEOUT
            )

            if result.returncode == 0:
                return jsonify({
                    "hasError": False,
                    "compilerError": None
                })
            else:
                # Return the stderr (or stdout depending on the compiler) as the error message
                error_msg = result.stderr.strip() or result.stdout.strip()
                return jsonify({
                    "hasError": True,
                    "compilerError": error_msg if error_msg else "Compilation failed without specific error output."
                })

        except subprocess.TimeoutExpired:
            return jsonify({
                "hasError": True,
                "compilerError": "Compilation timed out."
            })
        except Exception as e:
            return jsonify({
                "hasError": True,
                "compilerError": f"Internal compiler error: {str(e)}"
            })

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)