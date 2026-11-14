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
        'args': ['-std=c++17', '-Wall'],
        'extension_check': 'cpp'
    },
    '.ts': {
        'command': 'tsc',
        'args': ['--noEmit', '--target', 'es5'],
        'extension_check': 'ts'
    }
}

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    
    if not data or 'fileName' not in data or 'fileContent' not in data:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    file_name = data['fileName']
    file_content = data['fileContent']
    
    # Determine language by extension
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()

    if ext not in COMPILERS:
        return jsonify({"error": f"Unsupported file extension: {ext}"}), 400

    config = COMPILERS[ext]
    
    # Create a temporary directory to avoid collisions and cleanup
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Prepare the command
            # For C++, we compile to an object file. For TS, tsc --noEmit just checks types.
            cmd = [config['command']] + config['args']
            
            if ext == '.cpp':
                # g++ needs the input file and an output flag to avoid creating a.out in tmp
                cmd += [file_path, '-o', os.path.join(tmpdir, 'out')]
            else:
                # tsc needs the file path
                cmd += [file_path]

            # Execute the compiler
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )

            if process.returncode == 0:
                return jsonify({
                    "hasError": False,
                    "compilerError": None
                })
            else:
                # Return the stderr (or stdout if stderr is empty) as the compiler error
                error_msg = process.stderr.strip() or process.stdout.strip()
                return jsonify({
                    "hasError": True,
                    "compilerError": error_msg if error_msg else "Unknown compilation error"
                })

        except subprocess.TimeoutExpired:
            return jsonify({
                "hasError": True,
                "compilerError": "Compilation timed out after 10 seconds"
            })
        except Exception as e:
            return jsonify({
                "hasError": True,
                "compilerError": str(e)
            })

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)