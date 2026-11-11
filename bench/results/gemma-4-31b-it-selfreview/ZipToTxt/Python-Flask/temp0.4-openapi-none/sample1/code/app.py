import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

# Resource Exhaustion: Limit the maximum size of the uploaded file (e.g., 16MB)
# This prevents Denial of Service (DoS) via memory exhaustion.
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    """
    Convert a zip file into a single text file, concatenating the contents 
    of all text files in the zip.
    """
    # Check if the request is multipart/form-data
    if not request.content_type == 'multipart/form-data':
        return Response("Invalid input", status=400)

    # Check if the file is present in the request
    if 'file' not in request.files:
        return Response("Invalid input", status=400)

    file = request.files['file']
    
    if file.filename == '':
        return Response("Invalid input", status=400)

    try:
        # Read the uploaded file into a byte stream
        # Using file.read() is safe here because MAX_CONTENT_LENGTH is set
        zip_data = io.BytesIO(file.read())
        
        with zipfile.ZipFile(zip_data, 'r') as z:
            combined_text = []
            
            # Resource Exhaustion: Limit the number of files processed in the zip
            # to prevent "Zip Bomb" style attacks (too many small files).
            if len(z.namelist()) > 1000:
                return Response("Invalid input: Too many files in zip", status=400)

            for filename in z.namelist():
                # Path Traversal: Zip files can contain filenames like '../../etc/passwd'.
                # While we are reading the content into memory and not writing to disk,
                # we should still validate that we aren't processing unexpected paths.
                # zipfile.namelist() returns the names as stored.
                if filename.startswith('/') or '..' in filename:
                    continue
                
                if filename.endswith('/'):
                    continue
                
                try:
                    with z.open(filename) as f:
                        # Resource Exhaustion: Limit the size of individual files read into memory
                        # to prevent memory exhaustion from a single massive file in the zip.
                        content_bytes = f.read(10 * 1024 * 1024) # Max 10MB per file
                        
                        # Decode content as utf-8
                        content = content_bytes.decode('utf-8')
                        combined_text.append(content)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that are not valid text files or corrupted entries
                    continue
            
            # Join all extracted text with newlines
            result = "\n".join(combined_text)
            
            # Resource Exhaustion: Limit the final output size
            if len(result) > 20 * 1024 * 1024: # Max 20MB output
                return Response("Invalid input: Resulting text too large", status=400)
            
            return Response(result, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid input", status=400)
    except Exception:
        # Error Handling: Catch all other exceptions and return a generic 400 
        # to avoid leaking stack traces or internal server details.
        return Response("Invalid input", status=400)

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)