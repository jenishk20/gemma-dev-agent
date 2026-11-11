import os
import subprocess
import tempfile
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response

app = FastAPI(
    title="PDF Concatenation Service",
    description="A service that concatenates multiple PDF files into a single PDF.",
    version="1.0.0"
)

# Resource exhaustion limits
MAX_FILES = 50
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF."
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")
    
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail="Too many files uploaded.")

    # Create a temporary directory to hold the uploaded files and the result
    with tempfile.TemporaryDirectory() as temp_dir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(files):
                # Validate PDF extension
                if not file.filename.lower().endswith('.pdf'):
                    raise HTTPException(status_code=400, detail="Invalid input or missing files.")
                
                # Security: We ignore the user-provided filename entirely to prevent 
                # path traversal and filename-based attacks.
                # We use a generated safe filename inside the temp directory.
                safe_filename = f"input_{i}.pdf"
                file_path = os.path.join(temp_dir, safe_filename)
                
                # Resource exhaustion: Bound the size of the uploaded file
                size = 0
                with open(file_path, "wb") as buffer:
                    while chunk := await file.read(8192):
                        size += len(chunk)
                        if size > MAX_FILE_SIZE:
                            raise HTTPException(status_code=400, detail="File size exceeds limit.")
                        buffer.write(chunk)
                
                input_paths.append(file_path)

            # Define the output path
            output_path = os.path.join(temp_dir, "concatenated.pdf")

            # Security: Use a list for subprocess.run (shell=False by default).
            # This prevents shell injection as arguments are passed directly to the execve system call.
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute the CLI tool with a timeout to prevent DoS via hanging processes
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30,
                shell=False 
            )

            if result.returncode != 0:
                # Error handling: Do not leak stderr to the client
                raise HTTPException(status_code=500, detail="An error occurred while processing the files.")

            # Read the resulting PDF file
            with open(output_path, "rb") as f:
                pdf_content = f.read()

            return Response(
                content=pdf_content, 
                media_type="application/pdf"
            )

        except HTTPException as he:
            raise he
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
        except Exception:
            # Error handling: Catch all other exceptions to prevent leaking stack traces
            raise HTTPException(status_code=500, detail="An error occurred while processing the files.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)