import os
import subprocess
import tempfile
import uuid
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/concatenate', methods=['POST'])
def concatenate_pdfs():
    # Validate that 'files' is present in the request
    if 'files' not in request.files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    uploaded_files = request.files.getlist('files')
    
    if not uploaded_files:
        return jsonify({"error": "Invalid input or missing files."}), 400

    # Create a temporary directory to store the PDF fragments
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(uploaded_files):
                if not file.filename.lower().endswith('.pdf'):
                    return jsonify({"error": f"File {file.filename} is not a PDF."}), 400
                
                # Generate a unique filename to avoid collisions
                filename = f"input_{i}_{uuid.uuid4().hex}.pdf"
                filepath = os.path.join(tmpdir, filename)
                file.save(filepath)
                input_paths.append(filepath)

            # Define the output path for the concatenated PDF
            output_filename = f"concatenated_{uuid.uuid4().hex}.pdf"
            output_path = os.path.join(tmpdir, output_filename)

            # Construct the pdfunite command
            # pdfunite input1.pdf input2.pdf ... output.pdf
            command = ['pdfunite'] + input_paths + [output_path]
            
            # Execute the CLI tool
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                return jsonify({"error": f"An error occurred while processing the files: {result.stderr}"}), 500

            # Return the resulting PDF file
            return send_file(output_path, mimetype='application/pdf')

        except Exception as e:
            return jsonify({"error": f"An error occurred while processing the files: {str(e)}"}), 500

if __name__ == '__main__':
    # Start the webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)