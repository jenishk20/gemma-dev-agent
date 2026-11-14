import zipfile
import io
from flask import Flask, request, Response

app = Flask(__name__)

def is_text_file(filename):
    """
    Simple check to determine if a file is likely a text file based on extension.
    """
    text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.md', '.csv', '.xml'}
    import os
    _, ext = os.path.splitext(filename.lower())
    return ext in text_extensions

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    """
    Converts a zip file into a single text file by concatenating the contents 
    of all text files found within the archive.
    """
    # Check if the request contains the file part
    if 'file' not in request.files:
        return Response("No file part in the request", status=400)

    file = request.files['file']

    # If user does not select file, browser submits an empty part without filename
    if file.filename == '':
        return Response("No selected file", status=400)

    try:
        # Use BytesIO to handle the uploaded file in memory to avoid writing to disk
        zip_data = io.BytesIO(file.read())
        
        with zipfile.ZipFile(zip_data, 'r') as z:
            # Get list of all files in the zip
            namelist = z.namelist()
            
            combined_content = []
            
            for name in namelist:
                # Skip directories
                if name.endswith('/'):
                    continue
                
                # Only process files that look like text files to avoid binary corruption
                if is_text_file(name):
                    try:
                        with z.open(name) as f:
                            # Read content and decode as utf-8, ignoring errors for non-text chars
                            content = f.read().decode('utf-8', errors='ignore')
                            combined_content.append(content)
                    except Exception:
                        # Skip files that cannot be read
                        continue
            
            # Join all contents with a newline separator
            final_text = "\n".join(combined_content)
            
            return Response(final_text, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid zip file", status=400)
    except Exception as e:
        return Response(f"An error occurred: {str(e)}", status=400)

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)