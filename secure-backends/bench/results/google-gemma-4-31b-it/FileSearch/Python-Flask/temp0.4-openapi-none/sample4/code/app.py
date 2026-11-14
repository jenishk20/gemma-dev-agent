import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# The base directory where files are stored
BASE_DATA_DIR = "/data"

def safe_path_join(base, relative):
    """
    Ensures that the resulting path is within the base directory 
    to prevent directory traversal attacks.
    """
    # Normalize paths to remove '..' and '.'
    resolved_path = os.path.abspath(os.path.join(base, relative))
    if not resolved_path.startswith(os.path.abspath(base)):
        return None
    return resolved_path

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the starting directory for the search
    start_dir = BASE_DATA_DIR
    if search_dir_rel:
        start_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
        if start_dir is None or not os.path.isdir(start_dir):
            return jsonify({"error": "Invalid search directory"}), 400

    # If neither search parameter is provided, we can't search for anything specific
    if search_content is None and search_filename is None:
        return jsonify({"error": "Provide either search_content or search_filename"}), 400

    matched_files = []

    try:
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match (starts with)
                if search_filename and file.startswith(search_filename):
                    matched_files.append(full_path)
                    continue # Move to next file if filename matches

                # Check content match
                if search_content:
                    try:
                        # We open in binary mode or handle encoding to avoid crashes on non-text files
                        with open(full_path, 'r', errors='ignore') as f:
                            if search_content in f.read():
                                matched_files.append(full_path)
                    except Exception:
                        # Skip files that cannot be read
                        pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Remove duplicates if a file matched both filename and content
    return jsonify({"files": list(set(matched_files))}), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)