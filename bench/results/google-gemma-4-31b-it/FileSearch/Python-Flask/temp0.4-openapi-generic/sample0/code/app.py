import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Base directory where files are stored
BASE_DATA_DIR = "/data"

def safe_path_join(base, relative_path):
    """
    Ensures that the resulting path is within the base directory 
    to prevent directory traversal attacks.
    """
    if not relative_path:
        return base
    
    # Normalize and join
    joined = os.path.abspath(os.path.join(base, relative_path))
    # Check if the joined path starts with the base directory path
    if not joined.startswith(os.path.abspath(base)):
        return None
    return joined

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON input"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the starting directory
    target_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
    if target_dir is None:
        return jsonify({"error": "Invalid search directory"}), 400

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return jsonify({"files": []}), 200

    matched_files = []

    try:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check filename match (if provided)
                # The spec says "match the filename" or "start". 
                # We check if the filename starts with the search_filename string.
                if search_filename and not file.startswith(search_filename):
                    continue
                
                # 2. Check content match (if provided)
                if search_content:
                    try:
                        # Open in binary mode to avoid decoding errors on non-text files
                        with open(full_path, 'rb') as f:
                            content = f.read().decode('utf-8', errors='ignore')
                            if search_content not in content:
                                continue
                    except Exception:
                        # If file cannot be read, we skip it
                        continue
                
                matched_files.append(full_path)
                
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"files": matched_files}), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)