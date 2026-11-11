import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

def secure_filename_check(filename):
    """
    Basic check to ensure we aren't dealing with malicious paths, 
    though zipfile.read() handles the content in memory.
    """
    return filename.strip('/')

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

    if file.filename == '':
        return Response("No selected file", status=400)

    try:
        # Read the uploaded file into a byte stream
        zip_data = io.BytesIO(file.read())
        
        # Use zipfile to open the archive
        with zipfile.ZipFile(zip_data, 'r') as z:
            # Get a list of all files in the zip
            file_list = z.namelist()
            
            combined_text = []
            
            for filename in file_list:
                # We only want to process files (not directories)
                # and we assume text files are those ending in .txt or similar.
                # To be robust, we try to read and decode.
                if not filename.endswith('/') :
                    try:
                        with z.open(filename) as f:
                            # Read content and decode as utf-8
                            content = f.read().decode('utf-8')
                            combined_text.append(content)
                            # Add a newline between files to ensure separation
                            if not content.endswith('\n'):
                                combined_text.append('\n')
                    except (UnicodeDecodeError, zipfile.BadZipFile):
                        # Skip files that are not valid text/utf-8
                        continue
            
            # Join all extracted texts into one string
            result = "".join(combined_text)
            
            # Return as plain text
            return Response(result, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid zip file", status=400)
    except Exception as e:
        return Response(f"An error occurred: {str(e)}", status=400)

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)