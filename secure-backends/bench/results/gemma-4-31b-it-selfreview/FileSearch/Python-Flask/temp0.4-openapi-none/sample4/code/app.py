import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# The base directory where files are stored
BASE_DATA_DIR = os.path.abspath("/data")

# Resource exhaustion limits
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit for request body
MAX_FILE_READ_SIZE = 1 * 1024 * 1024   # 1MB limit for reading files to prevent memory exhaustion

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def safe_path_join(base, relative):
    """
    Strictly prevents path traversal.
    1. Rejects absolute paths.
    2. Rejects paths containing '..'.
    3. Validates that the final resolved path is within the base directory.
    """
    if not relative:
        return base
    
    # Reject absolute paths or paths attempting to climb up
    if os.path.isabs(relative) or '..' in relative:
        return None
    
    # Join and normalize
    resolved_path = os.path.abspath(os.path.join(base, relative))
    
    # Ensure the resolved path is still inside the base directory
    if not resolved_path.startswith(BASE_DATA_DIR):
        return None
        
    return resolved_path

@app.route('/search', methods=['POST'])
def search_files():
    # Ensure request body is JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input"}), 400

    # Validate input types to prevent unexpected behavior (e.g., passing lists where strings are expected)
    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    if search_content is not None and not isinstance(search_content, str):
        return jsonify({"error": "Invalid input"}), 400
    if search_filename is not None and not isinstance(search_filename, str):
        return jsonify({"error": "Invalid input"}), 400
    if search_dir_rel is not None and not isinstance(search_dir_rel, str):
        return jsonify({"error": "Invalid input"}), 400

    # Determine the starting directory for the search
    start_dir = BASE_DATA_DIR
    if search_dir_rel:
        start_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
        if start_dir is None or not os.path.isdir(start_dir):
            return jsonify({"error": "Invalid input"}), 400

    # If neither search parameter is provided, return 400 as per "Invalid input"
    if search_content is None and search_filename is None:
        return jsonify({"error": "Invalid input"}), 400

    matched_files = []

    try:
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match (starts with)
                if search_filename and file.startswith(search_filename):
                    matched_files.append(full_path)
                    continue 

                # Check content match
                if search_content:
                    try:
                        # Use a buffer to prevent reading massive files into memory (Resource Exhaustion)
                        with open(full_path, 'r', errors='ignore') as f:
                            content = f.read(MAX_FILE_READ_SIZE)
                            if search_content in content:
                                matched_files.append(full_path)
                    except (OSError, IOError):
                        # Skip files that cannot be read due to permissions or system errors
                        pass
    except Exception:
        # Generic catch to prevent leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

    # Remove duplicates and return
    return jsonify({"files": list(set(matched_files))}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)