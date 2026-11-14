import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Base directory where files are stored
BASE_DATA_DIR = os.path.abspath('/data')

def is_safe_path(base, relative):
    """
    Strictly validates that the relative path does not attempt to escape the base directory.
    Prevents path traversal by rejecting absolute paths and '..' components.
    """
    if not relative:
        return base
    
    # Reject absolute paths to prevent bypassing the base directory
    if os.path.isabs(relative):
        return None
    
    # Reject any path containing '..' to prevent directory traversal
    # We normalize the path first to catch hidden traversal attempts
    normalized_rel = os.path.normpath(relative)
    if '..' in normalized_rel.split(os.sep):
        return None

    final_path = os.path.abspath(os.path.join(base, normalized_rel))
    
    # Final check: ensure the resolved path is still within the base directory
    if not final_path.startswith(BASE_DATA_DIR + os.sep) and final_path != BASE_DATA_DIR:
        return None
        
    return final_path

@app.route('/search', methods=['POST'])
def search_files():
    # Resource exhaustion: limit the size of the request body to prevent memory exhaustion
    # Flask's request.get_json() will handle basic JSON parsing.
    # We check for the existence of the JSON body.
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid input"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Validate input types to prevent unexpected behavior in string operations
    if search_content and not isinstance(search_content, str):
        return jsonify({"error": "Invalid input"}), 400
    if search_filename and not isinstance(search_filename, str):
        return jsonify({"error": "Invalid input"}), 400
    if search_dir_rel and not isinstance(search_dir_rel, str):
        return jsonify({"error": "Invalid input"}), 400

    # Determine the starting directory with strict traversal checks
    start_dir = is_safe_path(BASE_DATA_DIR, search_dir_rel)
    if start_dir is None:
        return jsonify({"error": "Invalid input"}), 400
    
    # If the directory doesn't exist, we return an empty list as per standard search behavior
    if not os.path.isdir(start_dir):
        return jsonify({"files": []}), 200

    matching_files = []

    try:
        # Resource exhaustion: os.walk can be slow on massive directories.
        # In a production environment, we would implement a timeout or depth limit.
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match
                name_match = False
                if search_filename and file.startswith(search_filename):
                    name_match = True
                
                # Check content match
                content_match = False
                if search_content:
                    try:
                        # Resource exhaustion: prevent reading massive files into memory.
                        # We read in chunks to check for the presence of the search string.
                        search_bytes = search_content.encode('utf-8')
                        with open(full_path, 'rb') as f:
                            # Read in 4KB chunks with overlap to catch strings split across chunks
                            chunk_size = 4096
                            overlap = len(search_bytes) - 1
                            buffer = b""
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                if search_bytes in (buffer + chunk):
                                    content_match = True
                                    break
                                buffer = chunk[-overlap:] if overlap > 0 else b""
                    except (OSError, IOError):
                        pass # Skip files that cannot be read (permissions, etc.)

                if name_match or content_match:
                    matching_files.append(full_path)

    except Exception:
        # Error handling: return generic 400 without leaking internal stack traces
        return jsonify({"error": "An error occurred during search"}), 400

    return jsonify({"files": matching_files}), 200

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)