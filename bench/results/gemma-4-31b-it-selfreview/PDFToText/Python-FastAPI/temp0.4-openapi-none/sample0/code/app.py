import subprocess
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(
    title="PDF to Text Converter API",
    description="A simple API to convert PDF files to Text format.",
    version="1.0.0"
)

# Define a reasonable limit for uploaded files to prevent resource exhaustion (e.g., 10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024 

@app.post(
    "/convert",
    summary="Convert a PDF file to Text",
    description="Upload a PDF file to convert it into Text format.",
    responses={
        200: {"content": {"text/plain": {}}},
        400: {"description": "Bad Request - Invalid input or missing file"},
        500: {"description": "Internal Server Error - Conversion failed"},
    }
)
async def convert_pdf_to_text(file: UploadFile = File(...)):
    # 1. Validate file existence and extension
    # We ignore the provided filename for path creation to prevent path traversal
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file. Please upload a PDF file.")

    # 2. Resource Exhaustion: Bound the request size
    # Read the file in chunks to check size without loading everything into memory immediately
    content = bytearray()
    while True:
        chunk = await file.read(1024 * 64) # 64KB chunks
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    # 3. Secure Temporary File Handling
    # NamedTemporaryFile creates a file with a random name in a secure system directory,
    # preventing path traversal and filename collisions.
    temp_pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name

        # 4. Prevent Shell Injection
        # We use a list for arguments and shell=False (default in subprocess.run)
        # This ensures the input is not interpreted by a shell.
        # We also add a timeout to prevent Denial of Service via "PDF bombs" or hanging processes.
        process = subprocess.run(
            ["pdftotext", "-", temp_pdf_path], # Using '-' as input is not supported by all versions, 
                                              # but since we wrote to a file, we pass the path.
                                              # Correct usage for pdftotext is: pdftotext [options] <PDF-file> [-]
            # To avoid confusion and ensure we use the file we just wrote:
            # We actually want: pdftotext <input_pdf> - (to output to stdout)
            # Let's correct the argument list:
            # ["pdftotext", temp_pdf_path, "-"] 
            # Wait, the standard pdftotext usage for stdout is: pdftotext <file> -
            # Let's use the correct sequence:
            ["pdftotext", temp_pdf_path, "-"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30 # Prevent resource exhaustion/hanging
        )
        
        extracted_text = process.stdout
        return Response(content=extracted_text, media_type="text/plain")

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Conversion timed out.")
    except subprocess.CalledProcessError:
        # We do not leak the stderr to the user to avoid leaking internal system details
        raise HTTPException(status_code=500, detail="Conversion failed.")
    except Exception:
        # Generic catch to avoid leaking stack traces
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        # Clean up the temporary file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)