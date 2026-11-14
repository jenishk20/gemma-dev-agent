import io
import zipfile
from flask import Flask, request, Response

app = Flask(__name__)

def process_zip_to_text(zip_stream):
    """
    Reads a zip stream and concatenates the contents of all text files.
    Implements basic security checks to prevent ZipBomb attacks.
    """
    output_text = []
    MAX_SIZE = 10 * 1024 * 1024  # 10MB limit for total extracted content
    current_total_size = 0

    try:
        with zipfile.ZipFile(zip_stream) as z:
            # Sort files by name to ensure deterministic output
            for filename in sorted(z.namelist()):
                # Only process files (ignore directories)
                if z.getinfo(filename).is_dir():
                    continue
                
                try:
                    # Read file content
                    with z.open(filename) as f:
                        content = f.read()
                        
                        # Security check: Prevent decompression bombs
                        current_total_size += len(content)
                        if current_total_size > MAX_SIZE:
                            raise ValueError("Zip file content exceeds maximum allowed size.")

                        # Attempt to decode as utf-8, skip if binary/non-text
                        # We use 'replace' to avoid crashing on minor encoding issues
                        text_content = content.decode('utf-8', errors='replace')
                        
                        # Append filename as a header for clarity, then the content
                        output_text.append(f"--- File: {filename} ---\n")
                        output_text.append(text_content)
                        output_text.append("\n\n")
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that cannot be read as text
                    continue
    except zipfile.BadZipFile:
        return None, "Invalid zip file."
    except ValueError as e:
        return None, str(e)
    except Exception as e:
        return None, f"An unexpected error occurred: {str(e)}"

    return "".join(output_text), None

@app.route('/convert', methods=['POST'])
def convert():
    # Check if the file part is present in the request
    if 'file' not in request.files:
        return Response("No file part in the request", status=400, mimetype='text/plain')

    file = request.files['file']

    if file.filename == '':
        return Response("No selected file", status=400, mimetype='text/plain')

    # Read the uploaded file into a BytesIO stream for zipfile
    try:
        zip_data = io.BytesIO(file.read())
        result_text, error = process_zip_to_text(zip_data)
        
        if error:
            return Response(error, status=400, mimetype='text/plain')
        
        if result_text is None:
            return Response("Conversion failed", status=400, mimetype='text/plain')

        return Response(result_text, status=200, mimetype='text/plain')
    
    except Exception as e:
        return Response(f"Internal Server Error: {str(e)}", status=500, mimetype='text/plain')

if __name__ == '__main__':
    # Start the Flask app on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)