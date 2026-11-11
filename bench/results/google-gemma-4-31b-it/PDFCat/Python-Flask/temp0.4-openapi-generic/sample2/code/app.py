import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    """
    Concatenates multiple PDF files using the pdfunite CLI tool.
    """
    # Check if the request is multipart/form-data
    if not request.content_type == 'multipart/form-data':
        return jsonify({"error": "Content-Type must be multipart/form-data"}), 400

    # Get the list of files from the request
    files = request.files.getlist('files')

    if not files or len(files) == 0:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Create a unique temporary directory for this request to avoid collisions
    request_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_FOLDER, request_id)
    os.makedirs(temp_dir, exist_ok=True)

    input_paths = []
    try:
        # Save uploaded files to the temporary directory
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            
            # Security: Ensure we only process PDF files
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": f"File {file.filename} is not a PDF."}), 400
            
            # Use a sanitized filename to prevent path traversal
            safe_filename = f"input_{i}.pdf"
            file_path = os.path.join(temp_dir, safe_filename)
            file.save(file_path)
            input_paths.append(file_path)

        if len(input_paths) < 2:
            # If only one valid PDF was provided, we can just return it or error.
            # The schema implies concatenation, so we handle the single file case.
            if len(input_paths) == 1:
                return send_file(input_paths[0], mimetype='application/pdf')
            return jsonify({"error": "No valid PDF files provided."}), 400

        # Define output path
        output_path = os.path.join(temp_dir, "concatenated.pdf")

        # Execute pdfunite via subprocess
        # pdfunite input1.pdf input2.pdf ... output.pdf
        cmd = ['pdfunite'] + input_paths + [output_path]
        
        # Use subprocess.run for security; avoid shell=True
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({"error": f"An error occurred while processing the files: {result.stderr}"}), 500

        # Return the concatenated PDF file
        return send_file(output_path, mimetype='application/pdf')

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500
    
    finally:
        # Cleanup: Remove the temporary directory and all files within it
        # In a production environment, a background task or cron job might be better,
        # but for this API, we attempt to clean up after the response is sent.
        # Note: send_file might need the file to exist. 
        # To be safe with send_file, we can use a generator or a cleanup hook.
        # However, for this specific requirement, we'll rely on the OS temp cleanup 
        # or a simple attempt to remove files if not using send_file's default behavior.
        # Since send_file closes the file, we can't easily delete it in the same request.
        # But for the sake of this exercise, we will leave the cleanup logic minimal 
        # or use a custom response to ensure deletion.
        pass

# To properly clean up files after send_file, we wrap the response
from flask import after_this_request

def cleanup_temp_dir(path):
    import shutil
    try:
        shutil.rmtree(path)
    except Exception:
        pass

@app.route('/concatenate_safe', methods=['POST']) # Redefining logic to handle cleanup
def concatenate_pdfs_safe():
    # This is a helper to ensure the directory is deleted after the response is sent
    # Since the prompt asks for one file and a specific schema, I will integrate 
    # the cleanup into the main route using a custom response.
    pass

# Overriding the first function with a cleanup mechanism
@app.route('/concatenate', methods=['POST'])
def concatenate_final():
    if not request.content_type == 'multipart/form-data':
        return jsonify({"error": "Content-Type must be multipart/form-data"}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    request_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_FOLDER, request_id)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        input_paths = []
        for i, file in enumerate(files):
            if not file.filename.lower().endswith('.pdf'):
                shutil_cleanup(temp_dir)
                return jsonify({"error": f"File {file.filename} is not a PDF."}), 400
            
            path = os.path.join(temp_dir, f"in_{i}.pdf")
            file.save(path)
            input_paths.append(path)

        if not input_paths:
            shutil_cleanup(temp_dir)
            return jsonify({"error": "No valid PDF files provided."}), 400

        output_path = os.path.join(temp_dir, "out.pdf")
        
        if len(input_paths) == 1:
            # Just copy to output for consistency
            import shutil
            shutil.copy(input_paths[0], output_path)
        else:
            cmd = ['pdfunite'] + input_paths + [output_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                shutil_cleanup(temp_dir)
                return jsonify({"error": "An error occurred while processing the files."}), 500

        # Use a generator to send the file and then delete the directory
        def generate():
            with open(output_path, 'rb') as f:
                yield f.read()
            shutil_cleanup(temp_dir)

        # We use a custom response to ensure the file is read before the directory is deleted
        # However, for simplicity and reliability in Flask, we'll use a simpler approach:
        # send_file and accept that temp files stay until OS cleanup, OR use a custom response.
        # Let's use a custom response to be a "good citizen".
        
        response = send_file(output_path, mimetype='application/pdf')
        
        @after_this_request
        def remove_files(response):
            shutil_cleanup(temp_dir)
            return response
            
        return response

    except Exception as e:
        shutil_cleanup(temp_dir)
        return jsonify({"error": "An error occurred while processing the files."}), 500

def shutil_cleanup(path):
    import shutil
    try:
        shutil.rmtree(path)
    except:
        pass

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)