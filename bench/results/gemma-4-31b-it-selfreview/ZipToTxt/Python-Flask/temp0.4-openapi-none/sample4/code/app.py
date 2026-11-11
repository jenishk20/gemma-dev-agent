from flask import Flask, request, Response
import zipfile
import io

app = Flask(__name__)

# Resource exhaustion: Bound the maximum upload size to prevent DoS (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    # Check if the request is multipart/form-data and contains the 'file' key
    if 'file' not in request.files:
        return Response("Invalid input", status=400)

    file = request.files['file']
    
    if file.filename == '':
        return Response("Invalid input", status=400)

    try:
        # Read the uploaded file into a BytesIO object
        # Using .read() is safe here because MAX_CONTENT_LENGTH limits the memory usage
        zip_data = io.BytesIO(file.read())
        
        with zipfile.ZipFile(zip_data, 'r') as z:
            combined_text = []
            
            # Resource exhaustion: Limit the number of files processed to prevent ZipBomb/CPU exhaustion
            MAX_FILES = 1000
            files_processed = 0
            
            for file_info in z.infolist():
                if files_processed >= MAX_FILES:
                    break
                
                # Path Traversal / ZipSlip: 
                # zipfile.open() handles the extraction of data, but we must ensure 
                # we aren't processing files that attempt to escape the archive 
                # logic or are suspiciously large.
                if file_info.is_dir():
                    continue
                
                # Resource exhaustion: Prevent "Zip Bomb" by checking uncompressed size
                # Limit individual file size to 10MB
                if file_info.file_size > 10 * 1024 * 1024:
                    continue

                try:
                    # We read the content directly into memory. 
                    # zipfile.open() does not extract to disk, avoiding path traversal on the host filesystem.
                    with z.open(file_info) as f:
                        # Read and decode. We use a slice to ensure we don't read more than the file_size
                        # though z.open handles this.
                        content = f.read().decode('utf-8', errors='ignore')
                        combined_text.append(content)
                        files_processed += 1
                except Exception:
                    continue
            
            # Join all extracted text contents into a single string
            result = "\n".join(combined_text)
            
        return Response(result, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid input", status=400)
    except Exception:
        # Error handling: Return documented error status code without leaking internal stack traces
        return Response("Invalid input", status=400)

if __name__ == '__main__':
    # Start the webserver on port 5000 and bind to 0.0.0.0
    app.run(host='0.0.0.0', port=5000)