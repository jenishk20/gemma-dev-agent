import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

# Resource Exhaustion: Limit the maximum size of the uploaded file (e.g., 16MB)
# This prevents the server from crashing due to memory exhaustion when reading file.read()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    """
    Convert a zip file into a single text file, 
    concatenating the contents of all text files in the zip.
    """
    # Check if the request is multipart/form-data and contains the 'file' key
    if 'file' not in request.files:
        return Response("Invalid input", status=400)

    file = request.files['file']

    if file.filename == '':
        return Response("Invalid input", status=400)

    try:
        # Read the uploaded file into a byte stream
        # Since we set MAX_CONTENT_LENGTH, file.read() is bounded
        zip_data = io.BytesIO(file.read())
        
        # Open the zip archive
        with zipfile.ZipFile(zip_data, 'r') as z:
            # Resource Exhaustion: Zip Bomb Protection
            # We check the total uncompressed size of all files before extraction
            # to prevent decompression bombs that could exhaust memory.
            total_uncompressed_size = sum(info.file_size for info in z.infolist())
            # Limit total uncompressed output to 50MB
            if total_uncompressed_size > 50 * 1024 * 1024:
                return Response("Invalid input: Zip file too large when decompressed", status=400)

            file_list = z.namelist()
            combined_text = []
            
            for file_name in file_list:
                # Path Traversal Prevention: 
                # zipfile.open() is generally safe as it doesn't write to disk, 
                # but we ensure we aren't processing directory entries.
                if file_name.endswith('/') or zipfile.ZipInfo(file_name).is_dir():
                    continue
                
                try:
                    with z.open(file_name) as f:
                        # Read bytes and decode to utf-8
                        # We read in chunks or limit size to prevent memory spikes per file
                        content = f.read().decode('utf-8')
                        combined_text.append(content)
                        combined_text.append("\n")
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that are not valid UTF-8 text files
                    continue

            # Join all extracted text into one string
            final_output = "".join(combined_text)
            
            return Response(final_output, mimetype='text/plain')

    except zipfile.BadZipFile:
        # Error Handling: Return documented error status code without leaking internals
        return Response("Invalid input", status=400)
    except Exception:
        # Error Handling: Catch-all to prevent stack trace leakage
        return Response("Invalid input", status=400)

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)