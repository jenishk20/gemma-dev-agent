from flask import Flask, request, Response
import zipfile
import io

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert_zip_to_txt():
    # Check if the request is multipart/form-data and contains the 'file' key
    if 'file' not in request.files:
        return Response("Invalid input: No file provided", status=400)

    file = request.files['file']
    
    if file.filename == '':
        return Response("Invalid input: No selected file", status=400)

    try:
        # Read the uploaded file into a BytesIO object for zipfile to process
        zip_data = io.BytesIO(file.read())
        
        with zipfile.ZipFile(zip_data, 'r') as z:
            combined_text = []
            # Iterate through all files in the zip archive
            for file_info in z.infolist():
                # Skip directories
                if file_info.is_dir():
                    continue
                
                try:
                    # Read the content of the file
                    with z.open(file_info) as f:
                        # Attempt to decode as utf-8, ignore errors for non-text files
                        content = f.read().decode('utf-8', errors='ignore')
                        combined_text.append(content)
                except Exception:
                    # If a file cannot be read, we skip it
                    continue
            
            # Join all extracted text contents into a single string
            result = "\n".join(combined_text)
            
        return Response(result, mimetype='text/plain')

    except zipfile.BadZipFile:
        return Response("Invalid input: The uploaded file is not a valid zip archive", status=400)
    except Exception as e:
        return Response(f"An error occurred: {str(e)}", status=400)

if __name__ == '__main__':
    # Start the webserver on port 5000 and bind to 0.0.0.0
    app.run(host='0.0.0.0', port=5000)