import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# The base directory where files are stored
BASE_DATA_DIR = os.path.abspath("/data")

def safe_path_join(base, relative):
    """
    Strictly prevents path traversal.
    Rejects absolute paths and paths containing '..' to ensure the result 
    is always a subdirectory of the base.
    """
    if not relative:
        return base
    
    # Reject absolute paths to prevent bypassing the base directory
    if os.path.isabs(relative):
        return None
    
    # Reject any path containing '..' to prevent directory traversal
    # This is a stricter check than abspath/startswith to avoid symlink or 
    # complex encoding bypasses.
    normalized_rel = os.path.normpath(relative)
    if ".." in normalized_rel.split(os.sep):
        return None

    joined = os.path.join(base, normalized_rel)
    
    # Final verification: the resolved path must start with the base directory
    if not os.path.abspath(joined).startswith(BASE_DATA_DIR):
        return None
        
    return joined

@app.route('/search', methods=['POST'])
def search_files():
    # Resource Exhaustion: Bound request size (Flask default is usually 16MB, 
    # but we ensure we only process JSON)
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid input"}), 400

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Validate input types to prevent unexpected behavior in string operations
    if search_content is not None and not isinstance(search_content, str):
        return jsonify({"error": "Invalid input"}), 400
    if search_filename is not None and not isinstance(search_filename, str):
        return jsonify({"error": "Invalid input"}), 400
    if search_dir_rel is not None and not isinstance(search_dir_rel, str):
        return jsonify({"error": "Invalid input"}), 400

    # Path Traversal Protection
    start_dir = safe_path_join(BASE_DATA_DIR, search_dir_rel)
    
    if search_dir_rel is not None and start_dir is None:
        return jsonify({"error": "Invalid input"}), 400
    
    if start_dir is None:
        start_dir = BASE_DATA_DIR

    # If the directory doesn't exist on the server, return an empty list
    if not os.path.exists(start_dir) or not os.path.isdir(start_dir):
        return jsonify({"files": []}), 200

    matched_files = []

    try:
        # Resource Exhaustion: os.walk can be expensive. 
        # In a production environment, we would implement a depth limit or timeout.
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match
                if search_filename:
                    if file.startswith(search_filename):
                        matched_files.append(full_path)
                        # We continue to check content if search_content is also provided
                        # but we use a set later to handle duplicates.

                # Check content match
                if search_content:
                    try:
                        # Resource Exhaustion: Prevent reading massive files into memory.
                        # We read in chunks to check for the presence of the string.
                        with open(full_path, 'rb') as f:
                            # Using a buffer to avoid loading multi-GB files into RAM
                            # We read in 64KB chunks with a small overlap to catch strings split across chunks
                            buffer_size = 65536
                            overlap = len(search_content) - 1 if search_content else 0
                            chunk = f.read(buffer_size)
                            while chunk:
                                # Decode bytes to string, ignoring errors for binary files
                                content_str = chunk.decode('utf-8', errors='ignore')
                                if search_content in content_str:
                                    matched_files.append(full_path)
                                    break
                                
                                # Move back slightly to ensure we don't miss a word split by the buffer
                                if overlap > 0:
                                    # This is a simplified chunking search; for production, 
                                    # a more robust sliding window would be used.
                                    # We read the next chunk and prepend the overlap.
                                    prev_chunk_end = chunk[-overlap:] if len(chunk) >= overlap else chunk
                                    chunk = f.read(buffer_size)
                                    # Combine overlap with new chunk
                                    full_chunk = prev_chunk_end + chunk
                                    content_str = full_chunk.decode('utf-8', errors='ignore')
                                    if search_content in content_str:
                                        matched_files.append(full_path)
                                        break
                                    chunk = chunk # Continue loop with the new chunk
                                else:
                                    chunk = f.read(buffer_size)
                            
                    except (OSError, IOError):
                        # Skip files that cannot be read (permissions, etc.)
                        pass

    except Exception:
        # Error Handling: Return documented status code without leaking internal details
        return jsonify({"error": "Internal server error"}), 400

    # Remove duplicates and return
    unique_files = list(set(matched_files))
    return jsonify({"files": unique_files}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)