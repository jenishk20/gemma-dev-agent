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
    if not relative:
        return base
    
    # Normalize paths to remove '..' and '.'
    joined = os.path.abspath(os.path.join(base, relative))
    if not joined.startswith(os.path.abspath(base)):
        return None
    return joined

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the starting directory for the search
    start_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
    
    # If search_dir was provided but is outside /data, return 400
    if search_dir_rel and start_dir is None:
        return jsonify({"error": "Invalid search directory"}), 400
    
    # Default to /data if no valid search_dir is provided
    if start_dir is None:
        start_dir = BASE_DATA_DIR

    # If the directory doesn't exist on the server, return an empty list
    if not os.path.exists(start_dir) or not os.path.isdir(start_dir):
        return jsonify({"files": []}), 200

    matched_files = []

    try:
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match (starts with or equals)
                if search_filename:
                    if file.startswith(search_filename):
                        matched_files.append(full_path)
                        continue # Avoid adding the same file twice if content also matches

                # Check content match
                if search_content:
                    try:
                        # We open in binary mode to avoid decoding errors with non-text files
                        with open(full_path, 'rb') as f:
                            content = f.read().decode('utf-8', errors='ignore')
                            if search_content in content:
                                matched_files.append(full_path)
                    except Exception:
                        # Skip files that cannot be read
                        pass

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Remove duplicates in case a file matched both filename and content
    unique_files = list(set(matched_files))
    
    return jsonify({"files": unique_files}), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)