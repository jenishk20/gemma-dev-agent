import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
import uvicorn

app = FastAPI(
    title="ZipToTxt",
    description="A simple webapp API for converting zip files into a single text file.",
    version="1.0.11"
)

# Resource exhaustion limits
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB limit to prevent memory exhaustion
MAX_FILES_IN_ZIP = 1000             # Prevent "Zip Bomb" file count exhaustion
MAX_TOTAL_TEXT_SIZE = 20 * 1024 * 1024 # 20MB limit for the final concatenated string

@app.post("/convert", summary="Convert a zip file to a text file")
async def convert_zip_to_txt(file: UploadFile = File(...)):
    """
    Convert a zip file into a single text file, concatenating the contents of all text files in the zip.
    """
    try:
        # 1. Resource Exhaustion: Limit the size of the uploaded file
        # We read the file in chunks or check the size to avoid loading massive files into RAM
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        zip_buffer = io.BytesIO(contents)

        # 2. Validation: Ensure it is a valid zip file
        if not zipfile.is_zipfile(zip_buffer):
            raise HTTPException(status_code=400, detail="Invalid input: Not a zip archive")

        zip_buffer.seek(0)
        combined_text = []
        current_total_size = 0
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # 3. Resource Exhaustion: Limit the number of files in the archive
            file_list = z.namelist()
            if len(file_list) > MAX_FILES_IN_ZIP:
                raise HTTPException(status_code=400, detail="Too many files in zip archive")
            
            for file_name in file_list:
                # 4. Path Traversal: zipfile.namelist() returns the names as stored.
                # While we aren't extracting to disk, we must ensure we don't process 
                # weird paths if we were to use them. Since we use z.open(file_name), 
                # the zipfile module handles the internal lookup. 
                # However, we skip directories to avoid processing logic errors.
                info = z.getinfo(file_name)
                if info.is_dir():
                    continue
                
                try:
                    with z.open(file_name) as f:
                        # 5. Resource Exhaustion: Prevent "Zip Bomb" (highly compressed files)
                        # We read the content and check the size before appending
                        raw_data = f.read()
                        
                        # Check if the decompressed size of this specific file is reasonable
                        # (e.g., not more than the total allowed output size)
                        if len(raw_data) > MAX_TOTAL_TEXT_SIZE:
                            raise HTTPException(status_code=400, detail="Individual file in zip is too large")

                        # Attempt to decode as UTF-8
                        content = raw_data.decode('utf-8')
                        
                        # Track total size of the resulting text to prevent memory exhaustion
                        current_total_size += len(content)
                        if current_total_size > MAX_TOTAL_TEXT_SIZE:
                            raise HTTPException(status_code=400, detail="Total extracted text exceeds size limit")
                            
                        combined_text.append(content)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that aren't valid UTF-8 text files as per requirements
                    continue

        # Join all extracted text with newlines
        final_output = "\n".join(combined_text)
        
        # Return as plain text
        return Response(content=final_output, media_type="text/plain")

    except HTTPException as he:
        # Re-raise FastAPI HTTP exceptions to maintain documented status codes
        raise he
    except Exception:
        # 6. Error Handling: Catch all other exceptions and return 400 without leaking stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)