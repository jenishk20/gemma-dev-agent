import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    """
    Convert a zip file into a single text file, 
    concatenating the contents of all text files in the zip.
    """
    # Check if the request is multipart/form-data and contains the 'file' key
    if 'file' not in request.files:
        return Response("Invalid input: No file uploaded", status=400)

    file = request.files['file']

    if file.filename == '':
        return Response("Invalid input: No selected file", status=400)

    try:
        # Read the uploaded file into a byte stream
        zip_data = io.BytesIO(file.read())
        
        # Open the zip archive
        with zipfile.ZipFile(zip_data, 'r') as z:
            # Get a list of all files in the zip
            file_list = z.namelist()
            
            combined_text = []
            
            for file_name in file_list:
                # We only process files (ignore directories)
                # We attempt to read files that look like text files or simply try to decode them
                # To be safe and follow the prompt "contents of all text files", 
                # we filter by common text extensions or attempt decoding.
                if not file_name.endswith('/') : # Skip directories
                    try:
                        with z.open(file_name) as f:
                            # Read bytes and decode to utf-8
                            content = f.read().decode('utf-8')
                            combined_text.append(content)
                            # Add a newline between files to ensure separation
                            combined_text.append("\n")
                    except (UnicodeDecodeError, zipfile.BadZipFile):
                        # Skip files that are not valid UTF-8 text files
                        continue

            # Join all extracted text into one string
            final_output = "".join(combined_text)
            
            return Response(final_output, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid input: The uploaded file is not a valid zip archive", status=400)
    except Exception as e:
        return Response(f"An error occurred: {str(e)}", status=400)

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)