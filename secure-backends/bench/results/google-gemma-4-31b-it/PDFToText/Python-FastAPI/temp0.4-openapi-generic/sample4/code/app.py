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
        raise HTTPException(status_code=400, detail="Invalid input: Please upload a PDF file.")

    # Create a temporary directory to handle the file securely
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded file to disk
            # Using a chunked read to avoid memory exhaustion for large files
            with open(input_path, "wb") as buffer:
                while chunk := await file.read(8192):
                    buffer.write(chunk)

            # Execute pdftotext utility from poppler-utils
            # -layout preserves the physical layout of the text
            process = subprocess.run(
                ["pdftotext", "-layout", input_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the resulting text file
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as text_file:
                    content = text_file.read()
                
                # Return as plain text as per OpenAPI spec
                return Response(content=content, media_type="text/plain")
            else:
                raise Exception("pdftotext failed to create output file.")

        except subprocess.CalledProcessError as e:
            # Log the error internally and return 500
            print(f"Subprocess error: {e.stderr}")
            raise HTTPException(status_code=500, detail="Conversion failed during PDF processing.")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal Server Error - Conversion failed.")

if __name__ == "__main__":
    import uvicorn
    # Run the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)