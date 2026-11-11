import os
import subprocess
import tempfile
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="PDF Concatenation Service")

class ErrorResponse(BaseModel):
    error: str

@app.post(
    "/concatenate",
    responses={
        200: {"content": {"application/pdf": {}}},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF."
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a temporary directory to store uploaded files and the result
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save each uploaded file to the temp directory
            for i, file in enumerate(files):
                # Validate file extension
                if not file.filename.lower().endswith('.pdf'):
                    raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
                
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                input_paths.append(file_path)

            output_path = os.path.join(tmpdir, "concatenated.pdf")
            
            # Build the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute the CLI tool
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pdfunite error: {result.stderr}")

            # Read the resulting file
            with open(output_path, "rb") as f:
                pdf_content = f.read()

            return Response(content=pdf_content, media_type="application/pdf")

        except HTTPException as he:
            raise he
        except Exception as e:
            # Log the error internally and return a 500
            print(f"Internal Error: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred while processing the files.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)