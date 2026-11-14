import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Base directory where files are stored
BASE_DATA_DIR = "/data"

def safe_join(base, path):
    """
    Ensures that the resulting path is within the base directory 
    to prevent directory traversal attacks.
    """
    if not path or path == "/":
        return base
    
    # Normalize path and remove leading slashes to treat as relative
    normalized_path = os.path.normpath(path).lstrip('/')
    full_path = os.path.join(base, normalized_path)
    
    # Verify the final path is still under the base directory
    if not full_path.startswith(os.path.abspath(base)):
        raise PermissionError("Attempted directory traversal")
    
    return full_path

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # If neither content nor filename is provided, we can't search
    if search_content is None and search_filename is None:
        return jsonify({"error": "Provide either search_content or search_filename"}), 400

    try:
        # Determine the root directory for the search
        root_search_path = BASE_DATA_DIR
        if search_dir_rel:
            root_search_path = safe_join(BASE_DATA_DIR, search_dir_rel)

        if not os.path.isdir(root_search_path):
            return jsonify({"files": []}), 200

        matched_files = []

        # Walk through the directory tree
        for root, dirs, files in os.walk(root_search_path):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check Filename Match (starts with)
                if search_filename and file.startswith(search_filename):
                    matched_files.append(full_path)
                    continue # Avoid double counting if content also matches

                # 2. Check Content Match
                if search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid encoding crashes
                        # with non-text files.
                        with open(full_path, 'rb') as f:
                            # Reading in chunks to handle large files efficiently
                            content_bytes = search_content.encode('utf-8')
                            while True:
                                chunk = f.read(4096)
                                if not chunk:
                                    break
                                if content_bytes in chunk:
                                    matched_files.append(full_path)
                                    break
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        continue

        return jsonify({"files": matched_files}), 200

    except PermissionError:
        return jsonify({"error": "Invalid search directory"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)