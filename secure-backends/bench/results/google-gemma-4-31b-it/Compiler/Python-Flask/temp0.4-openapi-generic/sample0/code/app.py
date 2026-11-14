import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

# Security configuration: limit the size of the request body to prevent DoS
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

def run_compiler(filename, content):
    """
    Handles the logic of writing the file to a temporary directory and 
    running the appropriate compiler based on the file extension.
    """
    # Use a temporary directory to avoid polluting the filesystem and for security
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        
        # Basic security check: ensure the filename doesn't attempt path traversal
        # although tempfile.TemporaryDirectory helps, we sanitize the filename.
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(tmpdir, safe_filename)

        try:
            with open(file_path, 'w') as f:
                f.write(content)
        except Exception as e:
            return True, f"FileSystem Error: {str(e)}"

        # Determine compiler based on extension
        if safe_filename.endswith('.ts'):
            # TypeScript compiler (tsc)
            # --noEmit prevents generating .js files in the tmp dir
            # --esModuleInterop and --target are common defaults
            cmd = ['tsc', file_path, '--noEmit', '--target', 'es5']
        elif safe_filename.endswith('.cpp'):
            # C++ compiler (g++)
            # -fsyntax-only checks for compilation errors without producing an executable
            cmd = ['g++', '-fsyntax-only', file_path]
        else:
            return True, "Unsupported file extension. Please use .ts or .cpp"

        try:
            # Run the compiler. capture_output=True captures stdout and stderr.
            # timeout is critical to prevent infinite loops or hanging processes.
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                return False, None
            else:
                # Return the stderr as the compiler error
                error_msg = result.stderr.strip() or result.stdout.strip()
                return True, error_msg
        except subprocess.TimeoutExpired:
            return True, "Compilation timed out after 10 seconds."
        except Exception as e:
            return True, f"Internal Compiler Error: {str(e)}"

@app.route('/compile', methods=['POST'])
def compile_code():
    """
    Endpoint to compile a single-file code snippet.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    file_name = data.get('fileName')
    file_content = data.get('fileContent')
    
    if not file_name or not file_content:
        return jsonify({"error": "Missing fileName or fileContent"}), 400

    # Perform compilation
    has_error, compiler_error = run_compiler(file_name, file_content)
    
    return jsonify({
        "hasError": has_error,
        "compilerError": compiler_error
    }), 200

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)