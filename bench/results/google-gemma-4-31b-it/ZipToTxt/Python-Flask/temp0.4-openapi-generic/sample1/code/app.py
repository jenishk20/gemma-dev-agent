import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

def process_zip_to_text(zip_stream):
    """
    Extracts all files from the zip stream, attempts to decode them as text,
    and concatenates them into a single string.
    """
    combined_text = []
    
    try:
        with zipfile.ZipFile(zip_stream) as z:
            # Sort file names to ensure deterministic output order
            for filename in sorted(z.namelist()):
                # Skip directories
                if filename.endswith('/'):
                    continue
                
                try:
                    with z.open(filename) as file:
                        # Read bytes and decode to utf-8, ignoring errors to avoid 
                        # crashing on binary files that might be inside the zip
                        content = file.read().decode('utf-8', errors='ignore')
                        combined_text.append(content)
                except Exception:
                    # If a file cannot be read, we skip it
                    continue
                    
    except zipfile.BadZipFile:
        return None

    return "\n".join(combined_text)

@app.route('/convert', methods=['POST'])
def convert():
    """
    Endpoint to convert a uploaded zip file into a single text response.
    """
    # Check if the request is multipart/form-data
    if not request.content_type == 'multipart/form-data':
        return Response("Invalid content type. Expected multipart/form-data", status=400)

    # Check if the 'file' key exists in the request
    if 'file' not in request.files:
        return Response("No file part in the request", status=400)

    file_storage = request.files['file']

    if file_storage.filename == '':
        return Response("No selected file", status=400)

    # Use a BytesIO stream to avoid saving the file to disk (security best practice)
    zip_data = io.BytesIO(file_storage.read())
    
    result = process_zip_to_text(zip_data)
    
    if result is None:
        return Response("Invalid zip file", status=400)

    # Return the concatenated text as plain text
    return Response(result, mimetype='text/plain')

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)