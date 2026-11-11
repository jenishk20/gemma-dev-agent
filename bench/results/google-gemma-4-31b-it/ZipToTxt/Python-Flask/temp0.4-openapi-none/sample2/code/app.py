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
        return Response("No file part in the request", status=400)

    file = request.files['file']

    if file.filename == '':
        return Response("No selected file", status=400)

    try:
        # Read the uploaded file into a byte stream
        zip_data = io.BytesIO(file.read())
        
        with zipfile.ZipFile(zip_data, 'r') as z:
            # Get a list of all files in the zip
            file_list = z.namelist()
            
            combined_text = []
            
            for filename in file_list:
                # We only process files (skip directories)
                # In a real-world scenario, we might check extensions like .txt, .py, .md etc.
                # For this implementation, we attempt to read everything as text.
                try:
                    with z.open(filename) as f:
                        # Read bytes and decode to utf-8, ignoring errors for binary files
                        content = f.read().decode('utf-8', errors='ignore')
                        if content:
                            combined_text.append(content)
                except Exception:
                    # Skip files that cannot be read
                    continue

            # Join all contents with a newline separator
            final_output = "\n".join(combined_text)
            
            return Response(final_output, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid zip file", status=400)
    except Exception as e:
        return Response(f"An error occurred: {str(e)}", status=400)

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)