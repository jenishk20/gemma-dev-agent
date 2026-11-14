import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# The base directory where files are stored
BASE_DATA_DIR = os.path.abspath("/data")

# Resource exhaustion limits
MAX_REQUEST_BODY_SIZE = 1 * 1024 * 1024  # 1MB limit for JSON body
MAX_FILE_READ_SIZE = 10 * 1024 * 1024   # 10MB limit for reading file content to prevent memory exhaustion

def safe_path_join(base, relative):
    """
    Strictly prevents path traversal.
    """
    if not relative:
        return base
    
    # Reject absolute paths to prevent bypassing the base directory
    if os.path.isabs(relative):
        return None
    
    # Join and normalize the path to resolve '..' and '.'
    # Using os.path.normpath to clean the path before joining
    normalized_rel = os.path.normpath(relative)
    if normalized_rel.startswith("..") or "/../" in normalized_rel:
        return None

    final_path = os.path.abspath(os.path.join(base, normalized_rel))
    
    # Confirm the resolved path is still within the base directory
    if not final_path.startswith(BASE_DATA_DIR):
        return None
        
    return final_path

@app.route('/search', methods=['POST'])
def search_files():
    # Resource exhaustion: Bound request size
    if request.content_length and request.content_length > MAX_REQUEST_BODY_SIZE:
        return jsonify({"error": "Request body too large"}), 400

    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if data is None:
        return jsonify({"error": "Invalid input"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Path Traversal Prevention
    start_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
    if start_dir is None:
        # If search_dir was provided but failed safety checks, return 400
        if search_dir_rel is not None:
            return jsonify({"error": "Invalid input"}), 400
        start_dir = BASE_DATA_DIR

    # Check if the directory exists and is actually a directory
    if not os.path.isdir(start_dir):
        # If the user specified a dir that doesn't exist, it's an invalid input
        if search_dir_rel is not None:
            return jsonify({"error": "Invalid input"}), 400
        # If it's the base /data and it doesn't exist, return empty list (standard behavior)
        if start_dir == BASE_DATA_DIR:
            return jsonify({"files": []}), 200
        return jsonify({"error": "Invalid input"}), 400

    matching_files = []

    try:
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check filename match
                name_match = False
                if search_filename and isinstance(search_filename, str):
                    if file.startswith(search_filename):
                        name_match = True
                
                # 2. Check content match
                content_match = False
                if search_content and isinstance(search_content, str):
                    try:
                        # Resource exhaustion: Read only up to MAX_FILE_READ_SIZE
                        with open(full_path, 'rb') as f:
                            chunk = f.read(MAX_FILE_READ_SIZE)
                            if search_content.encode('utf-8') in chunk:
                                content_match = True
                    except (OSError, IOError):
                        # Skip files that cannot be read (permissions, etc.)
                        pass

                if name_match or content_match:
                    matching_files.append(full_path)

    except Exception:
        # Error handling: return documented status code, do not leak stack trace
        return jsonify({"error": "Internal server error"}), 400

    return jsonify({"files": matching_files}), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)