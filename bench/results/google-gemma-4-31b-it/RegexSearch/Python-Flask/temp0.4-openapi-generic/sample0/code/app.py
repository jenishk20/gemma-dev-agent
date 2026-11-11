import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

def safe_join(root, path):
    """
    Safely joins the root directory with a user-provided path to prevent 
    Directory Traversal attacks.
    """
    # Normalize the path to remove '..' and '.'
    normalized_path = os.path.normpath(path).lstrip(os.sep)
    joined_path = os.path.join(root, normalized_path)
    
    # Ensure the resulting path is still within the root directory
    if not joined_path.startswith(root):
        raise PermissionError("Attempted to access directory outside of root.")
    
    return joined_path

@app.route('/search', methods=['GET'])
def search_files():
    # Extract query parameters
    regex_pattern = request.args.get('regex')
    directory_param = request.args.get('directory', '')
    recursive_param = request.args.get('recursive', 'false').lower() == 'true'

    # Validation: regex is required
    if not regex_pattern:
        return jsonify({"error": "The 'regex' query parameter is required."}), 400

    # Validate and resolve the search directory
    try:
        search_path = safe_join(FILES_ROOT, directory_param)
        if not os.path.exists(search_path):
            return jsonify({"error": "The specified directory does not exist."}), 400
        if not os.path.isdir(search_path):
            return jsonify({"error": "The specified path is not a directory."}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid directory path: {str(e)}"}), 400

    # Compile regex to check for validity
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regular expression: {str(e)}"}), 400

    matching_files = []

    try:
        # Walk through files
        if recursive_param:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        # Calculate path relative to the requested directory
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only check files in the immediate directory
            for entry in os.scandir(search_path):
                if entry.is_file():
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)

    except Exception as e:
        return jsonify({"error": f"An error occurred while searching files: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """
    Reads file content and checks if it matches the regex.
    Handles binary files by skipping them or reading as bytes if needed.
    """
    try:
        # We open in 'r' mode with errors='ignore' to handle potential 
        # encoding issues in text files without crashing.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If a file cannot be read, we skip it
        return False
    return False

if __name__ == '__main__':
    # Ensure the files root exists so the app doesn't fail on first run
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)