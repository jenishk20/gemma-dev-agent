import subprocess
import tempfile
import os
import shutil
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
        200: {"description": "Successfully converted PDF to text", "content": {"text/plain": {}}},
        400: {"description": "Bad Request - Invalid input or missing file"},
        500: {"description": "Internal Server Error - Conversion failed"},
    }
)
async def convert_pdf_to_text(file: UploadFile = File(...)):
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid input: Please upload a PDF file.")

    # Create a temporary directory to handle the file securely
    temp_dir = tempfile.mkdtemp()
    try:
        # Define paths for input and output
        input_path = os.path.join(temp_dir, "input.pdf")
        output_path = os.path.join(temp_dir, "output.txt")

        # Save uploaded file to disk
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Execute pdftotext utility
        # -layout maintains the visual layout of the text
        # We use a list for arguments to prevent shell injection
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
            
            # Return as plain text response
            return Response(content=content, media_type="text/plain")
        else:
            raise HTTPException(status_code=500, detail="Conversion failed: Output file not created.")

    except subprocess.CalledProcessError as e:
        # Log the error internally if needed, return 500 to user
        raise HTTPException(status_code=500, detail=f"Internal Server Error - Conversion failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    # Run the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)