import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(title="PDF Concatenation Service", version="1.0.0")

@app.post("/concatenate", summary="Concatenate multiple PDF files")
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    """
    Accepts multiple PDF files and returns a single concatenated PDF.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a temporary directory to store uploaded files and the result
    # Using a temporary directory ensures isolation and prevents filename collisions
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        
        try:
            # Save uploaded files to the temporary directory
            for i, file in enumerate(files):
                # Validate that the file is a PDF by checking the content type or extension
                if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
                    raise HTTPException(status_code=400, detail=f"File {file.filename} is not a valid PDF.")
                
                # Use a sanitized filename to prevent path traversal attacks
                safe_name = f"input_{i}.pdf"
                file_path = os.path.join(tmpdir, safe_name)
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                input_paths.append(file_path)

            # Define the output path
            output_path = os.path.join(tmpdir, "concatenated.pdf")

            # Construct the command for pdfunite
            # pdfunite takes: input1 input2 ... output
            command = ["pdfunite"] + input_paths + [output_path]

            # Execute the command
            # We use a list for the command to avoid shell injection vulnerabilities
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True
            )

            # Read the resulting PDF file
            with open(output_path, "rb") as f:
                pdf_content = f.read()

            return Response(
                content=pdf_content, 
                media_type="application/pdf"
            )

        except subprocess.CalledProcessError as e:
            # Log the error internally if needed, return 500 to user
            raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
        except Exception as e:
            # Catch-all for other unexpected errors
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)