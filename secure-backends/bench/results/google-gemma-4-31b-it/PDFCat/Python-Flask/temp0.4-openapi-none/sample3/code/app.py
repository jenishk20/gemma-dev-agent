import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    # Check if 'files' key exists in the request
    if 'files' not in request.files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    files = request.files.getlist('files')
    
    if not files or len(files) == 0:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(files):
                if not file.filename.lower().endswith('.pdf'):
                    return jsonify({"error": "All uploaded files must be PDFs."}), 400
                
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                file.save(file_path)
                input_paths.append(file_path)

            # Define the output path
            output_path = os.path.join(tmpdir, "concatenated.pdf")

            # Use pdfunite from poppler-utils
            # Command: pdfunite file1.pdf file2.pdf ... output.pdf
            command = ['pdfunite'] + input_paths + [output_path]
            
            # Run the command
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({"error": f"An error occurred while processing the files: {result.stderr}"}), 500

            # Return the concatenated PDF file
            return send_file(output_path, mimetype='application/pdf')

        except Exception as e:
            return jsonify({"error": f"An error occurred while processing the files: {str(e)}"}), 500

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)