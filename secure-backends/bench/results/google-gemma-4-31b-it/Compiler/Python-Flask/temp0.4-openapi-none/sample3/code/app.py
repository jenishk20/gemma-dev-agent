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

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    
    if not data or 'fileName' not in data or 'fileContent' not in data:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    file_name = data['fileName']
    file_content = data['fileContent']
    
    # Determine extension
    _, ext = os.path.splitext(file_name)
    
    if ext not in COMPILERS:
        return jsonify({"error": f"Unsupported file extension: {ext}. Supported: .cpp, .ts"}), 400

    # Create a temporary directory to avoid file collisions and clutter
    temp_dir = tempfile.mkdtemp()
    try:
        # Write the file to the temp directory
        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

        # Run the compiler
        compiler_cfg = COMPILERS[ext]
        
        # For C++, we need to run in the temp dir
        # For TS, tsc --noEmit checks the file provided
        cmd = compiler_cfg['command']
        if ext == '.cpp':
            # g++ -c main.cpp
            full_cmd = cmd + [file_path]
        else:
            # tsc --noEmit main.ts
            full_cmd = cmd + [file_path]

        process = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            cwd=temp_dir
        )

        if process.returncode == 0:
            return jsonify({
                "hasError": False,
                "compilerError": None
            })
        else:
            # Combine stderr and stdout as some compilers use stdout for errors
            error_msg = (process.stderr or "").strip() or (process.stdout or "").strip()
            return jsonify({
                "hasError": True,
                "compilerError": error_msg
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)