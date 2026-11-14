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

    # Create a temporary directory to store the uploaded PDFs and the result
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temp directory
            for i, file in enumerate(files):
                if file.filename == '':
                    continue
                
                # Ensure we only process pdfs based on extension or assume binary
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                file.save(file_path)
                input_paths.append(file_path)

            if not input_paths:
                return jsonify({"error": "No valid PDF files provided."}), 400

            output_path = os.path.join(tmpdir, "concatenated.pdf")

            # Use pdfunite CLI: pdfunite file1.pdf file2.pdf ... output.pdf
            # Construct the command list
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute the command
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