import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# The base directory where files are stored
BASE_DATA_DIR = os.path.abspath("/data")

def safe_path_join(base, relative):
    """
    Strictly validates that the relative path does not attempt to escape the base directory.
    """
    if not relative:
        return base
    
    # Reject absolute paths to prevent bypassing the base directory
    if os.path.isabs(relative):
        return None
        
    # Reject paths containing '..' to prevent directory traversal
    # This is a defense-in-depth measure alongside abspath check
    if '..' in relative.split(os.sep) and '..' in relative.split('/'):
        return None
    # More robust check for '..' across different OS separators
    normalized_rel = os.path.normpath(relative)
    if normalized_rel.startswith('..') or '..' in normalized_rel.split(os.sep):
        return None

    joined = os.path.abspath(os.path.join(base, normalized_rel))
    
    # Confirm the resolved path is still within the base directory
    if joined.startswith(base + os.sep) or joined == base:
        return joined
    return None

@app.route('/search', methods=['POST'])
def search_files():
    # Resource exhaustion: Bound request size (e.g., 1MB)
    if request.content_length and request.content_length > 1024 * 1024:
        return jsonify({"error": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid input"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Validate input types to prevent unexpected behavior
    if not all(isinstance(x, (str, type(None))) for x in [search_content, search_filename, search_dir_rel]):
        return jsonify({"error": "Invalid input"}), 400

    # Determine the starting directory for the search
    start_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
    
    if start_dir is None or not os.path.exists(start_dir) or not os.path.isdir(start_dir):
        return jsonify({"error": "Invalid input"}), 400

    matched_files = []

    try:
        # Resource exhaustion: Limit the number of files scanned to prevent DoS
        files_scanned = 0
        MAX_FILES = 10000 

        for root, dirs, files in os.walk(start_dir):
            for file in files:
                files_scanned += 1
                if files_scanned > MAX_FILES:
                    break
                
                full_path = os.path.join(root, file)
                
                # Check filename match
                filename_match = False
                if search_filename and file.startswith(search_filename):
                    filename_match = True
                
                # Check content match
                content_match = False
                if search_content:
                    try:
                        # Resource exhaustion: Read file in chunks to prevent memory exhaustion
                        # Use binary mode to avoid encoding errors and handle large files safely
                        search_bytes = search_content.encode('utf-8')
                        with open(full_path, 'rb') as f:
                            # Read in chunks of 4KB
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
                        pass

                if filename_match or content_match:
                    matched_files.append(full_path)
            
            if files_scanned > MAX_FILES:
                break

    except Exception:
        # Error handling: Return documented error status without leaking stack traces
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"files": matched_files}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)