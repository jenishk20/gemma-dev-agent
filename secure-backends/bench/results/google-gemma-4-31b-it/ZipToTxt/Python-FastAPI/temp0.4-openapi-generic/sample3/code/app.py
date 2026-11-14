import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(
    title="ZipToTxt",
    description="A simple webapp API for converting zip files into a single text file.",
    version="1.0.11"
)

@app.post(
    "/convert",
    summary="Convert a zip file to a text file",
    description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.",
    response_class=PlainTextResponse
)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # Validate file extension for basic security
    if not file.filename and not file.filename.endswith('.zip'):
        # We check filename if available, but the primary check is the zipfile.is_zipfile
        pass

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)

        # Verify if the file is actually a zip file
        if not zipfile.is_zipfile(zip_buffer):
            raise HTTPException(status_code=400, detail="Invalid input: File is not a valid zip archive")

        # Reset buffer position after is_zipfile check
        zip_buffer.seek(0)
        
        combined_text = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Get list of files in zip
            file_list = z.namelist()
            
            for filename in file_list:
                # Security: Prevent ZipSlip/Path Traversal by ignoring entries with '..' or absolute paths
                if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
                    continue
                
                # Only process files (ignore directories)
                info = z.getinfo(filename)
                if info.is_dir():
                    continue
                
                try:
                    # Read the file content
                    with z.open(filename) as f:
                        # Attempt to decode as utf-8, ignore errors to handle binary files gracefully
                        # or skip files that aren't text-like.
                        content = f.read().decode('utf-8', errors='ignore')
                        combined_text.append(content)
                        # Add a newline between files to ensure separation
                        if not content.endswith('\n'):
                            combined_text.append('\n')
                except Exception:
                    # Skip files that cannot be read
                    continue

        if not combined_text:
            # Return empty string if no text files were found, or could be considered 400
            return ""

        return "".join(combined_text)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)