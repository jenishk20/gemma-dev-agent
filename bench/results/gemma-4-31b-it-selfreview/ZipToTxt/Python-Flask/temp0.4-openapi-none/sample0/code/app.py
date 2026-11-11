import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

# Resource exhaustion: Limit the maximum size of the uploaded file (e.g., 16MB)
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

    # Check if the user actually selected a file
    if file.filename == '':
        return Response("Invalid input", status=400)

    try:
        # Read the uploaded file into a bytes stream
        # Note: file.read() is bounded by MAX_CONTENT_LENGTH
        zip_data = io.BytesIO(file.read())
        
        # Open the zip file
        with zipfile.ZipFile(zip_data, 'r') as z:
            combined_text = []
            
            # Resource exhaustion: Limit the number of files processed to prevent "Zip Bomb" 
            # or CPU exhaustion from thousands of small files.
            MAX_FILES = 1000
            files_processed = 0
            
            for filename in z.namelist():
                if files_processed >= MAX_FILES:
                    break
                
                # Security: Zip files can contain directory entries. 
                # We only process files. We do not extract to disk, so path traversal 
                # (e.g. ../../etc/passwd) is mitigated as we only read the stream.
                if not filename.endswith('/') :
                    try:
                        # Resource exhaustion: Limit the size of individual file read
                        # to prevent memory exhaustion from a single massive compressed file.
                        with z.open(filename) as f:
                            # Read only up to 1MB per file to prevent memory spikes
                            content_bytes = f.read(1024 * 1024) 
                            content = content_bytes.decode('utf-8', errors='ignore')
                            combined_text.append(content)
                    except Exception:
                        # Skip files that cannot be read
                        continue
                    files_processed += 1
            
            # Join all contents with a newline
            final_output = "\n".join(combined_text)
            
        return Response(final_output, mimetype='text/plain')

    except zipfile.BadZipFile:
        # Error handling: Return documented error status code without leaking internals
        return Response("Invalid input", status=400)
    except Exception:
        # Error handling: Generic catch-all to prevent stack trace leakage
        return Response("Invalid input", status=400)

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)