import os
import subprocess
import tempfile
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response

app = FastAPI(title="PDF Concatenation Service", description="A service that concatenates multiple PDF files into a single PDF.")

# Resource exhaustion limits
MAX_FILES = 50
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file

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
    # Resource Exhaustion: Limit the number of files
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")
    
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail="Too many files uploaded.")

    # Create a temporary directory to store uploaded files and the result
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save uploaded files to the temporary directory
            for i, file in enumerate(files):
                # Path Traversal: We ignore the user-provided filename for the local filesystem
                # and use a generated index. We only check the extension for validation.
                filename = file.filename or "unknown.pdf"
                if not filename.lower().endswith('.pdf'):
                    raise HTTPException(status_code=400, detail=f"File {filename} is not a PDF.")
                
                # Resource Exhaustion: Bound request size
                # We read the file in chunks or check size to prevent memory exhaustion
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail=f"File {filename} exceeds size limit.")
                
                # Secure file path: use a controlled name inside the temp directory
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                input_paths.append(file_path)

            output_path = os.path.join(tmpdir, "concatenated.pdf")
            
            # Shell Injection Prevention: 
            # We use a list for the command and shell=False (default in subprocess.run).
            # This ensures that arguments are passed directly to the execve system call
            # and not interpreted by a shell.
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute the CLI tool with a timeout to prevent resource exhaustion (DoS)
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30, 
                shell=False
            )
            
            if result.returncode != 0:
                # Error Handling: We do not leak the stderr to the user to avoid leaking internal details
                raise Exception("pdfunite failed to process PDFs")

            # Read the resulting PDF file
            with open(output_path, "rb") as f:
                pdf_content = f.read()

            return Response(content=pdf_content, media_type="application/pdf")

        except HTTPException as he:
            raise he
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
        except Exception:
            # Error Handling: Catch all other exceptions and return a generic 500 as per spec
            # without leaking stack traces or internal system paths.
            raise HTTPException(status_code=500, detail="An error occurred while processing the files.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)