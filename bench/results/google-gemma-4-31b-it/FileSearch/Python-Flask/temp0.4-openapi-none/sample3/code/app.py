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
    
    # Resolve the absolute path
    joined = os.path.abspath(os.path.join(base, relative))
    # Check if the resolved path starts with the base directory
    if joined.startswith(os.path.abspath(base)):
        return joined
    return None

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
    
    if start_dir is None or not os.path.exists(start_dir):
        return jsonify({"error": "Invalid search directory"}), 400

    matched_files = []

    try:
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match (starts with or equals)
                filename_match = False
                if search_filename and file.startswith(search_filename):
                    filename_match = True
                
                # Check content match
                content_match = False
                if search_content:
                    try:
                        # We open in binary mode or with errors='ignore' to handle non-text files
                        with open(full_path, 'rb') as f:
                            # Search for the content as bytes
                            if search_content.encode('utf-8') in f.read():
                                content_match = True
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        pass

                # If either condition is met, add to list
                if filename_match or content_match:
                    matched_files.append(full_path)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"files": matched_files}), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)