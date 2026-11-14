import zipfile
import io
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import PlainTextResponse

app = FastAPI(
    title="ZipToTxt",
    description="A simple webapp API for converting zip files into a single text file.",
    version="1.0.11"
)

# Resource exhaustion limits
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB limit for the zip file
MAX_EXTRACTED_SIZE = 50 * 1024 * 1024  # 50 MB limit for total concatenated text

@app.post(
    "/convert",
    summary="Convert a zip file to a text file",
    description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.",
    response_class=PlainTextResponse
)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # Validate file extension to avoid processing non-zip files
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file must be a .zip archive.")

    try:
        # Resource Exhaustion: Bound request size
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit.")
        
        zip_buffer = io.BytesIO(contents)
        combined_text = []
        current_total_size = 0
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # ZipSlip/Path Traversal Prevention:
            # We do not extract files to the filesystem (no z.extract() or z.extractall()).
            # We use z.open() which returns a file-like object for the specific member.
            # This avoids path traversal vulnerabilities entirely.
            
            file_list = z.namelist()
            
            for filename in file_list:
                # Skip directories
                if filename.endswith('/'):
                    continue
                
                try:
                    with z.open(filename) as f:
                        # Resource Exhaustion: Prevent "Zip Bomb" by limiting read size per file
                        # and tracking total accumulated size.
                        chunk = f.read(MAX_EXTRACTED_SIZE) 
                        if not chunk:
                            continue
                            
                        # Attempt to decode as utf-8
                        data = chunk.decode('utf-8')
                        
                        current_total_size += len(data)
                        if current_total_size > MAX_EXTRACTED_SIZE:
                            raise HTTPException(status_code=400, detail="Extracted content exceeds maximum allowed limit.")
                            
                        combined_text.append(data)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip binary files or corrupted members
                    continue
        
        # Join all extracted text contents
        result = "\n".join(combined_text)
        return Response(content=result, media_type="text/plain")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid input: The file is not a valid zip archive.")
    except HTTPException as he:
        # Re-raise FastAPI HTTP exceptions
        raise he
    except Exception:
        # Error Handling: Catch all other exceptions to prevent leaking stack traces/internal details
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)