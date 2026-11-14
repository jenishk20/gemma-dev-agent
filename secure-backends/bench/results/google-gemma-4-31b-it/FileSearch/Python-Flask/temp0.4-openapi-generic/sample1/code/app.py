import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# The base directory where files are stored
BASE_DATA_DIR = os.path.abspath('/data')

def safe_path_join(base, relative_path):
    """
    Ensures that the resulting path is within the base directory 
    to prevent Path Traversal attacks.
    """
    if not relative_path:
        return base
    
    # Join and resolve to absolute path to remove '..' or '.'
    final_path = os.path.abspath(os.path.join(base, relative_path))
    
    if not final_path.startswith(BASE_DATA_DIR):
        return None
    return final_path

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    
    if data is None:
        return jsonify({"error": "Invalid JSON input"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the directory to search in
    target_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
    
    # If search_dir was provided but resolved outside /data, return 400
    if search_dir_rel and target_dir is None:
        return jsonify({"error": "Invalid search directory"}), 400
    
    # Default to /data if no valid directory is provided
    if target_dir is None:
        target_dir = BASE_DATA_DIR

    # If the target directory doesn't exist or isn't a directory, return empty list or 400
    if not os.path.isdir(target_dir):
        return jsonify({"files": []}), 200

    matched_files = []

    try:
        # Walk through the directory tree
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match (starts with)
                if search_filename and file.startswith(search_filename):
                    matched_files.append(full_path)
                    continue
                
                # Check content match
                if search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid decoding errors 
                        # with non-text files (like mp3s mentioned in the schema)
                        with open(full_path, 'rb') as f:
                            content_bytes = search_content.encode('utf-8')
                            # Read in chunks to avoid memory issues with huge files
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Remove duplicates if a file matched both filename and content
    unique_files = list(set(matched_files))
    
    return jsonify({"files": unique_files}), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)