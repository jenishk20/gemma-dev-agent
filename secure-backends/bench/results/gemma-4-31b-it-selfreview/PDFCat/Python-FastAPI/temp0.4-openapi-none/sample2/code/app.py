import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
import uvicorn

app = FastAPI(
    title="PDF Concatenation Service",
    description="A service that concatenates multiple PDF files into a single PDF.",
    version="1.0.0"
)

# Resource exhaustion limits
MAX_FILES = 50
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file
MAX_TOTAL_SIZE = 100 * 1024 * 1024 # 100 MB total

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF.",
    responses={
        200: {"content": {"application/pdf": {}}},
        400: {"description": "Bad Request - Invalid input or missing files."},
        500: {"description": "Internal Server Error - An error occurred while processing the files."}
    }
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    # Resource exhaustion: Bound number of files
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")
    
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail="Too many files uploaded.")

    # Create a temporary directory to store uploaded files
    # tempfile.mkdtemp is secure and creates a directory with restricted permissions
    temp_dir = tempfile.mkdtemp()
    input_paths = []
    total_size = 0
    
    try:
        for i, file in enumerate(files):
            # Resource exhaustion: Bound individual file size
            # We read in chunks to avoid loading massive files into memory at once
            file_path = os.path.join(temp_dir, f"input_{i}.pdf")
            
            with open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 64) # 64KB chunks
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > MAX_TOTAL_SIZE:
                        raise HTTPException(status_code=400, detail="Total upload size exceeded limit.")
                    f.write(chunk)
            
            # Check individual file size after writing
            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Individual file size exceeds limit.")
                
            input_paths.append(file_path)

        if len(input_paths) < 1:
            raise HTTPException(status_code=400, detail="Invalid input or missing files.")

        if len(input_paths) == 1:
            with open(input_paths[0], "rb") as f:
                data = f.read()
            return Response(content=data, media_type="application/pdf")

        output_path = os.path.join(temp_dir, "concatenated.pdf")
        
        # Security: Untrusted input reaching a shell
        # We use a list for arguments and shell=False (default) to prevent shell injection.
        # We do not use any user-provided filenames in the command, only our generated paths.
        command = ["pdfunite"] + input_paths + [output_path]
        
        # Execute the CLI tool with a timeout to prevent DoS via hanging processes
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            shell=False, 
            timeout=30
        )
        
        if result.returncode != 0:
            # Error handling: Do not leak internal stderr to the user
            raise Exception("pdfunite failed to process files")

        # Read the resulting file
        with open(output_path, "rb") as f:
            pdf_data = f.read()
            
        return Response(content=pdf_data, media_type="application/pdf")

    except HTTPException as he:
        # Re-raise FastAPI HTTP exceptions
        raise he
    except Exception as e:
        # Error handling: Catch all exceptions and return documented 500 error
        # No stack traces or internal details leaked to the response
        print(f"Internal Error: {str(e)}") 
        raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)