import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
BASE_DATA_DIR = "/data"

def safe_path_join(base, relative):
    """
    Ensures the resulting path is contained within the base directory 
    to prevent Directory Traversal attacks.
    """
    # Normalize paths to remove '..' and redundant separators
    final_path = os.path.abspath(os.path.join(base, relative))
    if not final_path.startswith(os.path.abspath(base)):
        return None
    return final_path

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir', "")

    # Determine the root directory for the search
    # If search_dir is provided, ensure it's a subpath of /data
    root_dir = BASE_DATA_DIR
    if search_dir_rel:
        root_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
        if root_dir is None or not os.path.isdir(root_dir):
            return jsonify({"error": "Invalid search directory"}), 400

    if not search_content and not search_filename:
        return jsonify({"error": "Provide either search_content or search_filename"}), 400

    matched_files = []

    try:
        # Walk through the directory tree
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Match by filename (starts with)
                if search_filename and file.startswith(search_filename):
                    matched_files.append(full_path)
                    continue # Move to next file if filename matches

                # 2. Match by content
                if search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid 
                        # decoding errors with non-text files
                        content_bytes = search_content.encode('utf-8')
                        with open(full_path, 'rb') as f:
                            # Reading in chunks to avoid memory issues with large files
                            while True:
                                chunk = f.read(1024 * 1024) # 1MB chunk
                                if not chunk:
                                    break
                                if content_bytes in chunk:
                                    matched_files.append(full_path)
                                    break
                    except (OSError, IOError):
                        # Skip files that cannot be read (permissions, etc)
                        continue

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"files": matched_files}), 200

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)