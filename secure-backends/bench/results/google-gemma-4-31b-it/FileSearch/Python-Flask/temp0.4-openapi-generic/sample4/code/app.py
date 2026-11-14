import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Define the base data directory
BASE_DATA_DIR = "/data"

def safe_join(base, path):
    """
    Ensures that the resulting path is within the base directory 
    to prevent directory traversal attacks.
    """
    if not path:
        return base
    
    # Normalize path and remove leading slashes to treat it as relative
    normalized_path = os.path.normpath(path).lstrip('/')
    full_path = os.path.join(base, normalized_path)
    
    # Ensure the resolved path starts with the base directory
    if not full_path.startswith(os.path.abspath(base)):
        raise PermissionError("Access denied: Path is outside the data directory")
    
    return full_path

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # If both search parameters are null, it's an invalid request based on the logic
    if search_content is None and search_filename is None:
        return jsonify({"error": "Either search_content or search_filename must be provided"}), 400

    try:
        # Resolve the search directory safely
        root_search_path = safe_join(BASE_DATA_DIR, search_dir_rel)
        
        if not os.path.exists(root_search_path) or not os.path.isdir(root_search_path):
            return jsonify({"files": []}), 200

        matched_files = []

        # Walk through the directory tree
        for root, dirs, files in os.walk(root_search_path):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check filename match (starts with)
                if search_filename and file.startswith(search_filename):
                    matched_files.append(full_path)
                    continue # Move to next file if filename matches to avoid double counting

                # 2. Check content match
                if search_content:
                    try:
                        # We open in binary mode or with errors='ignore' to handle non-text files safely
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            if search_content in f.read():
                                matched_files.append(full_path)
                    except Exception:
                        # Skip files that cannot be read
                        pass

        return jsonify({"files": matched_files}), 200

    except PermissionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)