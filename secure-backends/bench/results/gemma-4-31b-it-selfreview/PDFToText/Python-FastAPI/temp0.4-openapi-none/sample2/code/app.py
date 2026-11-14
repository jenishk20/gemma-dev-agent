import subprocess
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Response

app = FastAPI(
    title="PDF to Text Converter API",
    description="A simple API to convert PDF files to Text format.",
    version="1.0.0"
)

# Resource exhaustion limit: 10MB max upload size
MAX_FILE_SIZE = 10 * 1024 * 1024 

@app.post(
    "/convert",
    summary="Convert a PDF file to Text",
    description="Upload a PDF file to convert it into Text format.",
    responses={
        200: {"description": "Successfully converted PDF to text", "content": {"text/plain": {}}},
        400: {"description": "Bad Request - Invalid input or missing file"},
        500: {"description": "Internal Server Error - Conversion failed"},
    }
)
async def convert_pdf_to_text(file: UploadFile = File(...)):
    # 1. Validate file presence and extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid input: Please upload a PDF file.")

    # 2. Resource Exhaustion: Limit uploaded file size
    # We read the file in chunks to avoid loading massive files into memory at once
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use fixed filenames inside the temp directory to prevent path traversal 
            # via the user-supplied filename.
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.txt")

            size = 0
            with open(input_path, "wb") as f:
                while chunk := await file.read(8192):
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
                    f.write(chunk)

            # 3. Shell Injection Prevention: 
            # subprocess.run is called with a list (shell=False by default), 
            # which avoids shell interpretation of arguments.
            # We also add a timeout to prevent DoS via "PDF bombs" (resource exhaustion).
            try:
                subprocess.run(
                    ["pdftotext", "-layout", input_path, output_path],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30  # Prevent hanging processes
                )
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=500, detail="Conversion timed out.")
            except subprocess.CalledProcessError:
                # We do not leak e.stderr to the client to avoid leaking internal system details
                raise HTTPException(status_code=500, detail="Conversion failed.")

            # 4. Safe File Read
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                    text_content = f.read()
                return Response(content=text_content, media_type="text/plain")
            else:
                raise HTTPException(status_code=500, detail="Conversion failed to produce output.")

    except HTTPException as he:
        raise he
    except Exception:
        # Generic error handling to prevent leaking stack traces
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)