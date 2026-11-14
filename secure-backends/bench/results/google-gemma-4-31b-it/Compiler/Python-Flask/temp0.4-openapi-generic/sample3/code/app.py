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
        'ext': 'o'
    },
    '.ts': {
        'command': ['tsc'], 
        'ext': 'js'
    }
}

def run_compiler(filename, content):
    """
    Handles the execution of the compiler in a temporary directory 
    to prevent directory pollution and mitigate some security risks.
    """
    ext = os.path.splitext(filename)[1]
    if ext not in COMPILERS:
        return True, f"Unsupported file extension: {ext}"

    config = COMPILERS[ext]
    
    # Create a temporary directory for the compilation process
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        
        try:
            # Write the content to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Run the compiler command
            # We use a timeout to prevent Denial of Service via infinite loops/heavy compilation
            # We redirect stderr to stdout to capture the compiler error messages
            process = subprocess.run(
                config['command'] + [file_path],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=10 
            )
            
            if process.returncode == 0:
                return False, None
            else:
                # Return the combined output as the compiler error
                error_msg = process.stderr if process.stderr else process.stdout
                return True, error_msg.strip()
                
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out after 10 seconds."
        except Exception as e:
            return True, str(e)

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    
    file_name = data.get('fileName')
    file_content = data.get('fileContent')
    
    if file_name is None or file_content is None:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    # Basic security check: prevent directory traversal in fileName
    # Only allow the base name of the file
    safe_file_name = os.path.basename(file_name)
    
    has_error, error_message = run_compiler(safe_file_name, file_content)
    
    return jsonify({
        "hasError": has_error,
        "compilerError": error_message
    }), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)