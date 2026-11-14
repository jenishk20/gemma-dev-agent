import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

# Resource exhaustion: Limit the maximum allowed upload size (e.g., 16MB)
# This prevents memory exhaustion attacks via massive zip files.
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    """
    Convert a zip file into a single text file, 
    concatenating the contents of all text files in the zip.
    """
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return Response("Invalid input", status=400)

    file = request.files['file']

    if file.filename == '':
        return Response("Invalid input", status=400)

    try:
        # Read the uploaded file into a byte stream
        # Note: file.read() is bounded by MAX_CONTENT_LENGTH
        zip_data = io.BytesIO(file.read())
        
        with zipfile.ZipFile(zip_data, 'r') as z:
            # ZipBomb Protection: Check the uncompressed size of all files
            # to prevent resource exhaustion (decompression bombs).
            total_uncompressed_size = sum(info.file_size for info in z.infolist())
            if total_uncompressed_size > 50 * 1024 * 1024: # Limit to 50MB uncompressed
                return Response("Invalid input", status=400)

            file_list = z.namelist()
            combined_text = []
            
            for filename in file_list:
                # Path Traversal Protection: 
                # zipfile.open() can be tricked by filenames containing '..' or absolute paths.
                # We verify the filename does not attempt to escape the zip root.
                if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                    continue
                
                try:
                    # We use z.open which reads the file from the archive stream, 
                    # not from the local filesystem, mitigating traditional path traversal.
                    with z.open(filename) as f:
                        # Read bytes and decode to utf-8, ignoring errors for binary files.
                        # We read in chunks or limit the size per file to prevent memory spikes.
                        content = f.read(10 * 1024 * 1024).decode('utf-8', errors='ignore')
                        if content:
                            combined_text.append(content)
                except Exception:
                    # Skip files that cannot be read or are corrupted
                    continue

            # Join all contents with a newline separator
            final_output = "\n".join(combined_text)
            
            return Response(final_output, mimetype='text/plain')

    except zipfile.BadZipFile:
        # Error handling: Return documented error status code without leaking internals
        return Response("Invalid input", status=400)
    except Exception:
        # Generic catch-all to prevent stack trace leakage
        return Response("Invalid input", status=400)

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)