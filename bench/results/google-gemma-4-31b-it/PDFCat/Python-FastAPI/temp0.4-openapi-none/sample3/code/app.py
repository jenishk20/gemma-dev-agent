import os
import subprocess
import tempfile
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(title="PDF Concatenation Service", description="A service that concatenates multiple PDF files into a single PDF.")

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF.",
    responses={
        200: {"description": "Successfully concatenated the PDF files.", "content": {"application/pdf": {}}},
        400: {"description": "Bad Request - Invalid input or missing files."},
        500: {"description": "Internal Server Error - An error occurred while processing the files."},
    }
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a temporary directory to store uploaded files and the result
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save uploaded files to the temporary directory
            for i, file in enumerate(files):
                if not file.filename.lower().endswith('.pdf'):
                    raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
                
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                input_paths.append(file_path)

            output_path = os.path.join(tmpdir, "concatenated.pdf")
            
            # Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute the CLI tool
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Log the error internally if needed, then raise 500
                raise Exception(f"pdfunite error: {result.stderr}")

            # Read the resulting PDF file
            with open(output_path, "rb") as f:
                pdf_content = f.read()

            return Response(content=pdf_content, media_type="application/pdf")

        except HTTPException as he:
            raise he
        except Exception as e:
            # Return 500 for any internal processing errors
            raise HTTPException(status_code=500, detail=f"An error occurred while processing the files: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)