import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response
import uvicorn

app = FastAPI(
    title="PDF Concatenation Service",
    description="A service that concatenates multiple PDF files into a single PDF.",
    version="1.0.0"
)

@app.post(
    "/concatenate",
    summary="Concatenate multiple PDF files",
    description="Accepts multiple PDF files and returns a single concatenated PDF.",
    responses={
        200: {"content": {"application/pdf": {}}},
        400: {"description": "Bad Request - Invalid input or missing files."},
        500: {"description": "Internal Server Error - An error occurred while processing the files."}
    }
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a temporary directory to store uploaded files
    temp_dir = tempfile.mkdtemp()
    input_paths = []
    
    try:
        # Save uploaded files to disk
        for i, file in enumerate(files):
            if file.content_type != "application/pdf":
                # We don't strictly enforce content-type based on the schema, 
                # but it's good practice. We'll proceed but check extension.
                pass
            
            file_path = os.path.join(temp_dir, f"input_{i}.pdf")
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            input_paths.append(file_path)

        if len(input_paths) < 2:
            # If only one file is provided, we can just return it
            if len(input_paths) == 1:
                with open(input_paths[0], "rb") as f:
                    data = f.read()
                return Response(content=data, media_type="application/pdf")
            raise HTTPException(status_code=400, detail="Invalid input or missing files.")

        output_path = os.path.join(temp_dir, "concatenated.pdf")
        
        # Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
        command = ["pdfunite"] + input_paths + [output_path]
        
        # Execute the CLI tool
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"pdfunite error: {result.stderr}")

        # Read the resulting file
        with open(output_path, "rb") as f:
            pdf_data = f.read()
            
        return Response(content=pdf_data, media_type="application/pdf")

    except Exception as e:
        # Log the error if necessary
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)