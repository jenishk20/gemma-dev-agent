import subprocess
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import PlainTextResponse

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
        200: {"description": "Successfully converted PDF to text", "content": {"text/plain": {}}},
        400: {"description": "Bad Request - Invalid input or missing file"},
        500: {"description": "Internal Server Error - Conversion failed"},
    }
)
async def convert_pdf_to_text(file: UploadFile = File(...)):
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid input: Please upload a PDF file.")

    # Create a temporary directory to handle the file
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.txt")

        try:
            # Save the uploaded file to disk
            content = await file.read()
            with open(input_path, "wb") as f:
                f.write(content)

            # Use pdftotext utility from poppler-utils
            # -layout preserves the layout of the text
            process = subprocess.run(
                ["pdftotext", "-layout", input_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )

            # Read the resulting text file
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
                return PlainTextResponse(content=text_content)
            else:
                raise Exception("pdftotext failed to generate output file.")

        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"Conversion failed: {e.stderr}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)