import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration for compilers
COMPILERS = {
    '.cpp': {
        'command': 'g++',
        'args': ['-c'], # Compile only, do not link
        'extension_flag': None
    },
    '.ts': {
        'command': 'tsc',
        'args': ['--noEmit', '--esModuleInterop'], # Check types without outputting JS
        'extension_flag': None
    }
}

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
    ext = os.path.splitext(file_name)[1]
    if ext not in COMPILERS:
        return jsonify({"error": f"Unsupported file extension: {ext}"}), 400

    # Create a temporary directory to avoid polluting the workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
        except Exception as e:
            return jsonify({"hasError": True, "compilerError": str(e)}), 500

        config = COMPILERS[ext]
        
        # Build the command
        # For g++, we need to specify the input file.
        # For tsc, we specify the file to check.
        cmd = [config['command']] + config['args'] + [file_path]

        try:
            # Run the compiler and capture output
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10 # Prevent infinite loops or hanging processes
            )

            # g++ outputs errors to stderr. tsc outputs errors to stdout/stderr.
            error_output = process.stderr if process.stderr else process.stdout
            
            if process.returncode != 0:
                return jsonify({
                    "hasError": True,
                    "compilerError": error_output.strip() if error_output else "Compilation failed without specific error message."
                })
            else:
                return jsonify({
                    "hasError": False,
                    "compilerError": None
                })

        except subprocess.TimeoutExpired:
            return jsonify({"hasError": True, "compilerError": "Compilation timed out."})
        except Exception as e:
            return jsonify({"hasError": True, "compilerError": f"Internal server error: {str(e)}"})

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)