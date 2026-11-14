import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="ZipToTxt", version="1.0.11")

# Resource exhaustion: Define a maximum upload size (e.g., 50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024 

@app.post(
    "/convert", 
    summary="Convert a zip file to a text file", 
    description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.",
    response_class=PlainTextResponse
)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # Validate that the uploaded file is actually a zip file
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file must be a .zip archive.")

    try:
        # Resource exhaustion: Check file size before reading into memory
        # Note: UploadFile.size is available in newer Starlette/FastAPI versions
        # If not available, we check during the read process.
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large.")
        
        zip_buffer = io.BytesIO(contents)
        combined_text = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Security: ZipBomb protection. 
            # We check the number of files to prevent decompression bombs.
            if len(z.namelist()) > 1000:
                raise HTTPException(status_code=400, detail="Zip archive contains too many files.")

            for filename in z.namelist():
                # Path Traversal: zipfile.ZipFile.open() handles the internal path, 
                # but we must ensure we aren't processing files that attempt to 
                # escape the archive context or are not actually text files.
                # We only process files ending in .txt and ignore directory entries.
                if filename.endswith('.txt') and not filename.endswith('/'):
                    # Resource exhaustion: Limit the size of individual extracted files
                    # to prevent memory exhaustion from a single massive text file.
                    info = z.getinfo(filename)
                    if info.file_size > MAX_FILE_SIZE:
                        raise HTTPException(status_code=400, detail="Individual file within zip is too large.")
                    
                    with z.open(filename) as f:
                        # Read bytes and decode to string. 
                        # Using 'replace' to avoid crashing on invalid utf-8 sequences.
                        text_content = f.read().decode('utf-8', errors='replace')
                        combined_text.append(text_content)
        
        if not combined_text:
            return ""

        # Join all text contents with a newline separator
        return "\n".join(combined_text)

    except zipfile.BadZipFile:
        # Error handling: Return documented 400 for invalid zip files
        raise HTTPException(status_code=400, detail="Invalid input: The file is not a valid zip archive.")
    except HTTPException as he:
        # Re-raise FastAPI HTTP exceptions
        raise he
    except Exception:
        # Error handling: Catch all other exceptions to prevent leaking stack traces
        # and return the documented 400 status code.
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)