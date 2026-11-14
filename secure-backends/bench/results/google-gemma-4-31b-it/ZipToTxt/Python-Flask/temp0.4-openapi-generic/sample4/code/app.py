import zipfile
import io
from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    """
    Convert a zip file into a single text file, concatenating the contents 
    of all text files in the zip.
    """
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return Response("No file part in the request", status=400)

    file = request.files['file']

    # If the user does not select a file, the part exists but has no filename
    if file.filename == '':
        return Response("No selected file", status=400)

    try:
        # Read the uploaded file into a byte stream
        zip_data = io.BytesIO(file.read())
        
        # Use zipfile to open the stream
        with zipfile.ZipFile(zip_data) as z:
            # Get a list of all files in the archive
            namelist = z.namelist()
            
            combined_text = []
            
            for name in namelist:
                # Security: Prevent ZipSlip/Path Traversal by ignoring 
                # files that try to escape the archive root or are directories
                # zipfile.ZipFile.open handles the extraction safely within the archive
                
                # We only process files (not directories)
                # In zip files, directories usually end with '/'
                if name.endswith('/'):
                    continue
                
                try:
                    # Open the file within the zip
                    with z.open(name) as member:
                        # Attempt to decode the content as utf-8
                        # We use errors='ignore' or 'replace' to ensure the app doesn't crash on binary files
                        content = member.read().decode('utf-8', errors='ignore')
                        
                        # Only append if the content is not empty (optional)
                        if content:
                            combined_text.append(content)
                except Exception:
                    # Skip files that cannot be read
                    continue

            # Join all extracted text with a newline separator
            final_output = "\n".join(combined_text)
            
            return Response(final_output, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid zip file", status=400)
    except Exception as e:
        return Response(f"An error occurred: {str(e)}", status=400)

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)