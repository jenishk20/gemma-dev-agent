import os
import subprocess
import tempfile
import shutil
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(title="PDF Concatenation Service")

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF.",
    responses={
        200: {"content": {"application/pdf": {}}},
        400: {"description": "Bad Request - Invalid input or missing files."},
        500: {"description": "Internal Server Error - An error occurred while processing the files."},
    }
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    # Validation: Ensure files are provided and at least one file exists
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a temporary directory to store uploaded files and the result
    # Using a context manager for the directory is not possible with the return, 
    # so we use tempfile.mkdtemp and clean up manually.
    temp_dir = tempfile.mkdtemp()
    
    try:
        input_paths = []
        for i, file in enumerate(files):
            # Validate file extension
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
            
            # Secure filename: use a generated name to avoid path traversal or collisions
            file_path = os.path.join(temp_dir, f"input_{i}.pdf")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            input_paths.append(file_path)

        # Define output path
        output_path = os.path.join(temp_dir, "concatenated.pdf")

        # Construct the command for pdfunite
        # pdfunite takes input files and the final output file as the last argument
        command = ["pdfunite"] + input_paths + [output_path]

        # Execute the command
        # We use a list for the command to avoid shell injection vulnerabilities
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=True
        )

        # Read the resulting PDF content
        with open(output_path, "rb") as f:
            pdf_content = f.read()

        return Response(content=pdf_content, media_type="application/pdf")

    except subprocess.CalledProcessError as e:
        # Log the error if needed and return 500
        raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary directory and all files within it
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)