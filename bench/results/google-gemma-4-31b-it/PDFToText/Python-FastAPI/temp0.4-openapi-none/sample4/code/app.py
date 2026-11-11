import subprocess
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(
    title="PDF to Text Converter API",
    description="A simple API to convert PDF files to Text format.",
    version="1.0.0"
)

class ErrorResponse(BaseModel):
    error: str

@app.post(
    "/convert",
    summary="Convert a PDF file to Text",
    description="Upload a PDF file to convert it into Text format.",
    responses={
        200: {"content": {"text/plain": {}}},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def convert_pdf_to_text(file: UploadFile = File(...)):
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid input or missing file. Please upload a PDF file.")

    # Create temporary files to handle the conversion via pdftotext CLI
    # pdftotext usually writes to a file or stdout
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        try:
            # Save uploaded file to temp location
            content = await file.read()
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name

            # We use pdftotext from poppler-utils. 
            # Running 'pdftotext input.pdf -' outputs the text to stdout.
            process = subprocess.run(
                ["pdftotext", temp_pdf_path, "-"],
                capture_output=True,
                text=True,
                check=True
            )
            
            extracted_text = process.stdout
            
            # Return as plain text response
            return Response(content=extracted_text, media_type="text/plain")

        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
        finally:
            # Cleanup temporary file
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)