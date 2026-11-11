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
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return Response("Invalid input: No file provided", status=400)

    file = request.files['file']

    # Check if the user actually selected a file
    if file.filename == '':
        return Response("Invalid input: No file selected", status=400)

    try:
        # Read the uploaded file into a bytes stream
        zip_data = io.BytesIO(file.read())
        
        # Open the zip file
        with zipfile.ZipFile(zip_data, 'r') as z:
            combined_text = []
            
            # Iterate through all files in the zip
            for filename in z.namelist():
                # We only want to process files, not directories
                if not filename.endswith('/') :
                    try:
                        # Read file content
                        with z.open(filename) as f:
                            # Attempt to decode as utf-8, ignoring errors for non-text files
                            content = f.read().decode('utf-8', errors='ignore')
                            combined_text.append(content)
                    except Exception:
                        # Skip files that cannot be read
                        continue
            
            # Join all contents with a newline
            final_output = "\n".join(combined_text)
            
        return Response(final_output, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid input: The uploaded file is not a valid zip file", status=400)
    except Exception as e:
        return Response(f"An error occurred: {str(e)}", status=400)

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)