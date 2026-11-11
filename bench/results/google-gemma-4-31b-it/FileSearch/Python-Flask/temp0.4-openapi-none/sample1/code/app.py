import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Base directory where files are stored
BASE_DATA_DIR = '/data'

def safe_path_join(base, relative):
    """
    Ensures that the resulting path is within the base directory 
    to prevent directory traversal attacks.
    """
    if not relative:
        return base
    
    # Join and normalize the path
    final_path = os.path.abspath(os.path.join(base, relative))
    # Check if the final path starts with the base directory path
    if not final_path.startswith(os.path.abspath(base)):
        return None
    return final_path

@app.route('/search', methods=['POST'])
def search_files():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the starting directory
    start_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
    if start_dir is None or not os.path.isdir(start_dir):
        # If search_dir is provided but invalid/out of bounds, return 400
        # If it's just not provided, we use BASE_DATA_DIR
        if search_dir_rel:
            return jsonify({"error": "Invalid search directory"}), 400
        start_dir = BASE_DATA_DIR

    # If the base data directory doesn't exist on the system, return empty list
    if not os.path.exists(start_dir):
        return jsonify({"files": []}), 200

    matching_files = []

    try:
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match (starts with or equals)
                name_match = False
                if search_filename and file.startswith(search_filename):
                    name_match = True
                
                # Check content match
                content_match = False
                if search_content:
                    try:
                        # We open in binary mode and check for bytes to avoid decoding errors 
                        # with non-text files (like mp3s mentioned in the schema)
                        with open(full_path, 'rb') as f:
                            if search_content.encode('utf-8') in f.read():
                                content_match = True
                    except (OSError, IOError):
                        pass # Skip files that cannot be read

                if name_match or content_match:
                    matching_files.append(full_path)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"files": matching_files}), 200

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)