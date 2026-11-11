import subprocess
import tempfile
import os
from pathlib import Path
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
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")

    # Create a temporary directory to handle the file securely
    with tempfile.TemporaryDirectory() as tmpdirname:
        input_path = Path(tmpdirname) / file.filename
        output_path = Path(tmpdirname) / "output.txt"

        try:
            # Save the uploaded file to the temporary path
            with input_path.open("wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # Execute pdftotext utility
            # -layout preserves the physical layout of the text
            result = subprocess.run(
                ["pdftotext", str(input_path), str(output_path)],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the resulting text file
            if output_path.exists():
                extracted_text = output_path.read_text(encoding="utf-8")
                return Response(content=extracted_text, media_type="text/plain")
            else:
                raise Exception("pdftotext failed to produce an output file.")

        except subprocess.CalledProcessError as e:
            # Log the error internally if needed, return 500 to user
            raise HTTPException(status_code=500, detail=f"Conversion failed: {e.stderr}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)