import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.join(os.getcwd(), 'files')

@app.route('/search', methods=['GET'])
def search_files():
    # Extract query parameters
    regex_pattern = request.args.get('regex')
    directory_rel = request.args.get('directory', '')
    recursive_str = request.args.get('recursive', 'false').lower()
    recursive = recursive_str == 'true'

    if not regex_pattern:
        return jsonify({"error": "Missing required parameter: regex"}), 400

    # Validate and compile regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    # Construct absolute path to search directory and ensure it's within FILES_ROOT
    # This prevents directory traversal attacks
    search_path = os.path.abspath(os.path.join(FILES_ROOT, directory_rel))
    if not search_path.startswith(os.path.abspath(FILES_ROOT)):
        return jsonify({"error": "Directory path is outside the allowed root directory"}), 400

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "Specified directory does not exist or is not a directory"}), 400

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        # Calculate path relative to the search_path as per schema
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only files directly in search_path
            for entry in os.scandir(search_path):
                if entry.is_file():
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to check if a file's content matches the regex."""
    try:
        # We open in binary mode and decode to handle potential encoding issues 
        # or simply read as text. Using 'utf-8' with 'ignore' to prevent crashes on binary files.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If file cannot be read, we skip it
        return False
    return False

if __name__ == '__main__':
    # Ensure the files root directory exists for the app to function
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    app.run(host='0.0.0.0', port=5000)