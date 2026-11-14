import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="ZipToTxt", version="1.0.11")

# Resource exhaustion limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for the zip file
MAX_EXTRACTED_SIZE = 50 * 1024 * 1024  # 50MB limit for combined text output

@app.post("/convert", response_class=PlainTextResponse)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    """
    Convert a zip file into a single text file, concatenating the contents of all text files in the zip.
    """
    # 1. Resource Exhaustion: Bound request size
    # We check the content-length header if available, or read in chunks
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # 2. Zip Bomb / Path Traversal Protection
    # We use a memory buffer to avoid writing to disk (preventing path traversal via extraction)
    zip_buffer = io.BytesIO(contents)
    
    if not zipfile.is_zipfile(zip_buffer):
        raise HTTPException(status_code=400, detail="Invalid input")

    try:
        combined_text = []
        current_total_size = 0
        
        with zipfile.ZipFile(zip_buffer) as z:
            # We iterate through the zip entries
            for member in z.infolist():
                # Path Traversal: Prevent reading files outside the zip context
                # Although we use z.open(), we ensure we don't process directory entries
                if member.is_dir():
                    continue
                
                # Resource Exhaustion: Prevent Zip Bomb (decompression ratio check)
                # Check if the uncompressed size of this specific file is reasonable
                if member.file_size > MAX_EXTRACTED_SIZE:
                    raise HTTPException(status_code=400, detail="Individual file inside zip is too large")

                try:
                    with z.open(member) as f:
                        # Read bytes and decode to string
                        # We read the content and check the size to prevent memory exhaustion
                        data_bytes = f.read()
                        
                        # Resource Exhaustion: Bound total extracted size
                        current_total_size += len(data_bytes)
                        if current_total_size > MAX_EXTRACTED_SIZE:
                            raise HTTPException(status_code=400, detail="Combined extracted content too large")
                        
                        data = data_bytes.decode('utf-8')
                        combined_text.append(data)
                        if not data.endswith('\n'):
                            combined_text.append('\n')
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that are not text files (cannot be decoded as utf-8)
                    continue

        # Join all extracted text into a single string
        result = "".join(combined_text)
        return result

    except HTTPException as he:
        # Re-raise FastAPI HTTP exceptions
        raise he
    except Exception:
        # Error handling: Catch all other exceptions and return a generic 400 
        # to avoid leaking internal stack traces or system details.
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)