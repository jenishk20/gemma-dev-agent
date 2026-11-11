import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="ZipToTxt")

def is_safe_path(filename: str) -> bool:
    """
    Basic check to prevent ZipSlip/Path Traversal attacks.
    Ensures the filename doesn't try to escape the current directory.
    """
    return not (filename.startswith("/") or ".." in filename)

@app.post("/convert", summary="Convert a zip file to a text file", response_class=PlainTextResponse)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    """
    Convert a zip file into a single text file, concatenating the contents of all text files in the zip.
    """
    # Validate file extension
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file must be a .zip archive.")

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            all_text = []
            
            # Iterate through files in the zip
            for member in z.namelist():
                # Security check: prevent path traversal
                if not is_safe_path(member):
                    continue
                
                # Only process files (not directories)
                # We check if the member is a file by attempting to read it and checking if it's not a directory
                info = z.getinfo(member)
                if info.is_dir():
                    continue
                
                try:
                    # Read file content
                    with z.open(member) as f:
                        # Attempt to decode as utf-8. If it fails, it's likely not a text file.
                        content = f.read().decode('utf-8')
                        all_text.append(content)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that aren't valid UTF-8 text
                    continue
            
            # Join all contents with a newline
            result_text = "\n".join(all_text)
            return Response(content=result_text, media_type="text/plain")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid input: The file is not a valid zip archive.")
    except Exception as e:
        # Generic error handling to avoid leaking internal details while signaling a 400/500
        raise HTTPException(status_code=400, detail=f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    # Start the server on port 5000
    uvicorn.run(app, host="0.0.0.0", port=5000)