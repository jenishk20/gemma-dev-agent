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
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file. Please upload a PDF file.")

    # Create a temporary file to store the uploaded PDF
    # We use a temporary directory to ensure cleanup
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        try:
            content = await file.read()
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    try:
        # Execute pdftotext utility
        # pdftotext [options] PDF-file [text-file]
        # If [text-file] is omitted, it prints to stdout
        process = subprocess.run(
            ["pdftotext", temp_pdf_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        extracted_text = process.stdout
        return Response(content=extracted_text, media_type="text/plain")

    except subprocess.CalledProcessError as e:
        # pdftotext returns non-zero if it fails to parse the PDF
        raise HTTPException(status_code=500, detail=f"Conversion failed: {e.stderr or str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)