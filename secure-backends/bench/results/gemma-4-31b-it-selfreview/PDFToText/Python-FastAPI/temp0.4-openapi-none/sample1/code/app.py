import subprocess
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI(
    title="PDF to Text Converter API",
    description="A simple API to convert PDF files to Text format.",
    version="1.0.0"
)

# Resource exhaustion limit: 10MB
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
    # Validate file presence and extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid input: Please upload a PDF file.")

    # Resource exhaustion: Bound request size
    # Note: FastAPI/Starlette reads the stream; we check the size during read
    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Error reading uploaded file.")

    # Path Traversal Prevention: 
    # We do NOT use the user-provided filename in any path. 
    # We use a hardcoded filename inside a secure temporary directory.
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve absolute path of the temp directory to ensure we stay within it
        base_dir = os.path.realpath(tmpdir)
        input_path = os.path.join(base_dir, "input.pdf")
        output_path = os.path.join(base_dir, "output.txt")

        try:
            # Save the uploaded file to disk
            with open(input_path, "wb") as f:
                f.write(content)

            # Shell Injection Prevention:
            # 1. Use a list for arguments (subprocess.run does not invoke shell by default).
            # 2. shell=False is the default.
            # 3. We use hardcoded paths, not user-supplied strings.
            # 4. Added a timeout to prevent resource exhaustion (DoS) from malicious PDFs.
            subprocess.run(
                ["pdftotext", "-layout", input_path, output_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Prevent hanging on "PDF bombs"
            )

            # Read the resulting text file
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                    text_content = f.read()
                return PlainTextResponse(content=text_content)
            else:
                raise Exception("Conversion utility did not produce output.")

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Conversion timed out.")
        except subprocess.CalledProcessError:
            # Error handling: Do not leak stderr/internal details to the client
            raise HTTPException(status_code=500, detail="Conversion failed due to an internal error.")
        except Exception:
            # Error handling: Generic error to prevent leaking stack traces
            raise HTTPException(status_code=500, detail="Internal Server Error occurred during conversion.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)