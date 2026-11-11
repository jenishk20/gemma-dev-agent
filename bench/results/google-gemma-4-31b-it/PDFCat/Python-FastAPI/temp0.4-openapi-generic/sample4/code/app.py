import os
import subprocess
import tempfile
import shutil
import uuid
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
    description="Accepts multiple PDF files and returns a single concatenated PDF.",
    responses={
        200: {"description": "Successfully concatenated the PDF files.", "content": {"application/pdf": {}}},
        400: {"description": "Bad Request - Invalid input or missing files."},
        500: {"description": "Internal Server Error - An error occurred while processing the files."},
    }
)
async def concatenate_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Invalid input or missing files.")

    # Create a unique temporary directory for this request to avoid collisions
    temp_dir = tempfile.mkdtemp(prefix=f"pdf_concat_{uuid.uuid4().hex}_")
    
    try:
        input_paths = []
        
        # Save uploaded files to the temp directory
        for i, file in enumerate(files):
            if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
                # Clean up the directory if we encounter an invalid file early
                shutil.rmtree(temp_dir)
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
            
            file_path = os.path.join(temp_dir, f"input_{i}.pdf")
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            input_paths.append(file_path)

        # Define output path
        output_path = os.path.join(temp_dir, "output.pdf")

        # Construct the command for pdfunite
        # pdfunite input1.pdf input2.pdf ... output.pdf
        command = ["pdfunite"] + input_paths + [output_path]

        # Execute the command
        # We use a list for the command to avoid shell injection vulnerabilities
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            check=True
        )

        # Read the resulting PDF
        with open(output_path, "rb") as f:
            pdf_content = f.read()

        return Response(content=pdf_content, media_type="application/pdf")

    except subprocess.CalledProcessError as e:
        # Log the error internally if needed, return 500 to client
        print(f"pdfunite error: {e.stderr}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the files.")
    finally:
        # Ensure the temporary directory is always cleaned up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)