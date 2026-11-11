import os
import subprocess
import tempfile
import shutil
import uuid
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="PDF Concatenation Service")

class ErrorResponse(BaseModel):
    error: str

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF.",
    responses={
        200: {"content": {"application/pdf": {}}},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    # Validate that files were provided
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a unique temporary directory to store uploaded files and the result
    # This prevents race conditions and ensures security between concurrent requests
    temp_dir = tempfile.mkdtemp(prefix="pdf_concat_")
    
    try:
        input_paths = []
        
        # Save uploaded files to the temporary directory
        for i, file in enumerate(files):
            # Validate file extension for basic security
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
            
            # Use a sanitized filename to prevent path traversal attacks
            safe_filename = f"input_{i}_{uuid.uuid4().hex}.pdf"
            file_path = os.path.join(temp_dir, safe_filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            input_paths.append(file_path)

        # Define the output path
        output_path = os.path.join(temp_dir, "concatenated_result.pdf")

        # Construct the command for pdfunite
        # pdfunite [input_files] [output_file]
        command = ["pdfunite"] + input_paths + [output_path]

        # Execute the CLI tool
        # shell=False is used to prevent shell injection vulnerabilities
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True
        )

        # Read the resulting PDF content
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
    finally:
        # Clean up the temporary directory and all files within it
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)