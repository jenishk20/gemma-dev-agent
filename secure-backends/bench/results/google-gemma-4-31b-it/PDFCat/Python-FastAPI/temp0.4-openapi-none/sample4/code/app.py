import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response
import uvicorn

app = FastAPI(title="PDF Concatenation Service", version="1.0.0")

@app.post("/concatenate")
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    """
    Accepts multiple PDF files and returns a single concatenated PDF using pdfunite.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a temporary directory to store uploaded files and the result
    temp_dir = tempfile.mkdtemp()
    input_paths = []
    
    try:
        # Save uploaded files to the temp directory
        for i, file in enumerate(files):
            if file.content_type != "application/pdf" and not file.filename.endswith(".pdf"):
                # We continue but we could raise 400 here. 
                # For robustness, we ensure the extension is .pdf for pdfunite
                filename = f"file_{i}.pdf"
            else:
                filename = f"file_{i}.pdf"
            
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            input_paths.append(file_path)

        if len(input_paths) < 2:
            # If only one file is provided, just return that file
            if len(input_paths) == 1:
                with open(input_paths[0], "rb") as f:
                    content = f.read()
                return Response(content=content, media_type="application/pdf")
            raise HTTPException(status_code=400, detail="Invalid input or missing files.")

        output_path = os.path.join(temp_dir, "concatenated.pdf")
        
        # Construct the pdfunite command: pdfunite input1.pdf input2.pdf ... output.pdf
        command = ["pdfunite"] + input_paths + [output_path]
        
        # Execute the CLI tool
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"pdfunite error: {result.stderr}")

        # Read the resulting PDF
        with open(output_path, "rb") as f:
            pdf_content = f.read()

        return Response(content=pdf_content, media_type="application/pdf")

    except Exception as e:
        # Log the error if needed, then return 500 as per schema
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
    
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)