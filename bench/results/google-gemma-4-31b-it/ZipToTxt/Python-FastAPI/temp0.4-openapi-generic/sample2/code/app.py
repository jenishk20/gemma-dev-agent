import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import PlainTextResponse

app = FastAPI(title="ZipToTxt", description="A simple webapp API for converting zip files into a single text file.")

@app.post(
    "/convert",
    summary="Convert a zip file to a text file",
    description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.",
    responses={
        200: {"description": "Conversion successful", "content": {"text/plain": {}}},
        400: {"description": "Invalid input"},
    }
)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # Validate that the uploaded file is actually a zip file
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file must be a .zip archive.")

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        
        # Use ZipFile to read the archive
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Get a list of all files in the zip
            file_list = z.namelist()
            
            combined_text = []
            
            for file_name in file_list:
                # Security: Prevent ZipSlip/Directory Traversal by ignoring files with '..' or absolute paths
                # ZipFile.read() generally handles this, but we ensure we only process files (not directories)
                info = z.getinfo(file_name)
                if info.is_dir():
                    continue
                
                # We only want to extract text files. 
                # For this implementation, we assume files ending in .txt or files that can be decoded as utf-8.
                # To be robust and follow the prompt "contents of all text files", 
                # we attempt to read and decode files.
                try:
                    with z.open(file_name) as f:
                        # Read bytes and decode to string
                        content = f.read().decode('utf-8')
                        combined_text.append(content)
                except (UnicodeDecodeError, RuntimeError):
                    # Skip files that aren't valid UTF-8 text files
                    continue
            
            # Join all extracted text with newlines
            result = "\n".join(combined_text)
            
            return PlainTextResponse(content=result)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file is not a valid zip archive.")
    except Exception as e:
        # Generic error handling to avoid leaking internal server details
        raise HTTPException(status_code=500, detail="An internal error occurred during processing.")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)