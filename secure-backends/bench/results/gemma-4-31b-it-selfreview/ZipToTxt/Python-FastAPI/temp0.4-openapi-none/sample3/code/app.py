import zipfile
import io
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response

app = FastAPI(title="ZipToTxt", description="A simple webapp API for converting zip files into a single text file.")

# Resource exhaustion limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit to prevent memory exhaustion
MAX_FILES_IN_ZIP = 1000           # Limit number of files to prevent "Zip Bomb" (DoS)
MAX_TOTAL_TEXT_SIZE = 50 * 1024 * 1024 # 50MB total extracted text limit

@app.post("/convert", summary="Convert a zip file to a text file", description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.")
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # 1. Resource Exhaustion: Limit uploaded file size
    # Note: FastAPI/Starlette reads the file into memory or spool file. 
    # We check the size before processing.
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size too large")

    try:
        # Use BytesIO to treat the bytes as a file-like object
        with zipfile.ZipFile(io.BytesIO(contents)) as z:
            # 2. Resource Exhaustion: Prevent Zip Bomb (too many files)
            namelist = z.namelist()
            if len(namelist) > MAX_FILES_IN_ZIP:
                raise HTTPException(status_code=400, detail="Too many files in zip archive")

            all_text = []
            total_extracted_size = 0

            for name in namelist:
                # 3. Path Traversal: Ensure the filename is not malicious.
                # zipfile.open() handles the extraction, but we must ensure we don't 
                # process entries that attempt to escape directories (though we aren't writing to disk).
                # We check for absolute paths or '..' to be safe.
                if name.startswith('/') or '..' in name:
                    continue # Skip dangerous paths

                # Only process files (not directories)
                if not name.endswith('/'):
                    try:
                        # Use z.open() which is safe as it returns a stream
                        with z.open(name) as f:
                            # 4. Resource Exhaustion: Limit size of individual file content
                            # We read in chunks or check the file size from ZipInfo
                            info = z.getinfo(name)
                            if info.file_size > MAX_TOTAL_TEXT_SIZE:
                                raise HTTPException(status_code=400, detail="Individual file in zip is too large")
                            
                            data_bytes = f.read()
                            # Decode to utf-8, ignoring errors to avoid crashing on binary data
                            data = data_bytes.decode('utf-8', errors='ignore')
                            
                            all_text.append(data)
                            total_extracted_size += len(data)
                            
                            # 5. Resource Exhaustion: Limit total accumulated text size
                            if total_extracted_size > MAX_TOTAL_TEXT_SIZE:
                                raise HTTPException(status_code=400, detail="Total extracted text size exceeds limit")
                                
                    except Exception:
                        # Skip files that cannot be opened
                        continue
            
            # Join all contents with newlines
            result = "\n".join(all_text)
            
            return Response(content=result, media_type="text/plain")
            
    except zipfile.BadZipFile:
        # 6. Error Handling: Return documented 400 for invalid input
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except HTTPException as he:
        # Re-raise our resource limit exceptions
        raise he
    except Exception:
        # 6. Error Handling: Catch-all to prevent leaking stack traces/internal details
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)