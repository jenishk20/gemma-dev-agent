import os
import subprocess
import tempfile
import shutil
import uuid
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(
    title="PDF Concatenation Service",
    description="A service that concatenates multiple PDF files into a single PDF.",
    version="1.0.0"
)

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF.",
    responses={
        200: {"description": "Successfully concatenated the PDF files.", "content": {"application/pdf": {}}},
        400: {"description": "Bad Request - Invalid input or missing files."},
        500: {"description": "Internal Server Error - An error occurred while processing the files."},
    }
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a unique temporary directory to avoid collisions and race conditions
    temp_dir = tempfile.mkdtemp(prefix="pdf_concat_")
    
    try:
        input_paths = []
        for file in files:
            # Validate that the file is a PDF based on filename
            if not file.filename.lower().endswith('.pdf'):
                # Cleanup already created files in temp_dir before raising
                shutil.rmtree(temp_dir)
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
            
            # Secure filename to prevent path traversal
            safe_name = f"{uuid.uuid4()}.pdf"
            file_path = os.path.join(temp_dir, safe_name)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            input_paths.append(file_path)

        if len(input_paths) < 1:
            shutil.rmtree(temp_dir)
            raise HTTPException(status_code=400, detail="No valid PDF files provided.")

        output_path = os.path.join(temp_dir, "concatenated.pdf")

        # Construct the command for pdfunite
        # pdfunite [input files] [output file]
        command = ["pdfunite"] + input_paths + [output_path]

        # Execute the CLI tool
        # We use a list for arguments to prevent shell injection
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=False
        )

        if result.returncode != 0:
            shutil.rmtree(temp_dir)
            raise HTTPException(
                status_code=500, 
                detail=f"An error occurred while processing the files: {result.stderr}"
            )

        # Read the resulting file into memory
        with open(output_path, "rb") as f:
            pdf_content = f.read()

        # Cleanup temporary directory
        shutil.rmtree(temp_dir)

        return Response(content=pdf_content, media_type="application/pdf")

    except HTTPException:
        raise
    except Exception as e:
        # Ensure cleanup happens even on unexpected errors
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the files: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)