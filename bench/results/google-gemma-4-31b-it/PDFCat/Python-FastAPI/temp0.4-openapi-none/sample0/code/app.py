import os
import subprocess
import tempfile
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(
    title="PDF Concatenation Service",
    description="A service that concatenates multiple PDF files into a single PDF.",
    version="1.0.0"
)

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF."
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a temporary directory to hold the uploaded files and the result
    with tempfile.TemporaryDirectory() as temp_dir:
        input_paths = []
        try:
            # Save each uploaded file to the temporary directory
            for i, file in enumerate(files):
                # Basic validation for PDF extension
                if not file.filename.lower().endswith('.pdf'):
                    raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
                
                file_path = os.path.join(temp_dir, f"input_{i}.pdf")
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                input_paths.append(file_path)

            # Define the output path
            output_path = os.path.join(temp_dir, "concatenated.pdf")

            # Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
            command = ["pdfunite"] + input_paths + [output_path]
            
            # Execute the CLI tool
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                # Log the error internally and return 500
                print(f"pdfunite error: {result.stderr}")
                raise HTTPException(status_code=500, detail="An error occurred while processing the files.")

            # Read the resulting PDF file
            with open(output_path, "rb") as f:
                pdf_content = f.read()

            return Response(
                content=pdf_content, 
                media_type="application/pdf"
            )

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred while processing the files.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)