import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="ZipToTxt", version="1.0.11")

@app.post("/convert", response_class=PlainTextResponse)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    """
    Convert a zip file into a single text file, concatenating the contents of all text files in the zip.
    """
    # Validate that the uploaded file is a zip file
    if not zipfile.is_zipfile(file.file):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file is not a valid zip archive.")

    try:
        # Read the file content into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        
        combined_text = []
        
        with zipfile.ZipFile(zip_buffer) as z:
            # Get list of all files in the zip
            file_list = z.namelist()
            
            for filename in file_list:
                # We only process files (ignore directories)
                # We check for common text extensions or assume text if it's not a directory
                # In a real scenario, we might check MIME types, but here we filter by common text extensions
                # or simply attempt to decode as utf-8.
                
                # Skip directories
                if filename.endswith('/'):
                    continue
                
                try:
                    with z.open(filename) as f:
                        # Read bytes and decode to string
                        data = f.read().decode('utf-8')
                        combined_text.append(data)
                        # Add a newline between files if not present to ensure separation
                        if not data.endswith('\n'):
                            combined_text.append('\n')
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that are not text files (cannot be decoded as utf-8)
                    continue

        # Join all extracted text into a single string
        result = "".join(combined_text)
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)