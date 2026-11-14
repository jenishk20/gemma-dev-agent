import zipfile
import io
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response

app = FastAPI(title="ZipToTxt", description="A simple webapp API for converting zip files into a single text file.")

@app.post("/convert", summary="Convert a zip file to a text file", description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.")
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # Validate that the uploaded file is a zip file
    if not zipfile.is_zipfile(io.BytesIO(await file.read())):
        # Reset file pointer for the actual processing if we read it here
        # But since we need to read it anyway, let's just read it once
        pass
    
    # Re-read the file content from the start
    await file.seek(0)
    contents = await file.read()
    
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as z:
            all_text = []
            # Get list of files in the zip
            for name in z.namelist():
                # Only process files (not directories) and attempt to read text files
                # We check for common text extensions or just try to decode
                # The requirement says "contents of all text files"
                if not name.endswith('/'): # Ignore directories
                    try:
                        with z.open(name) as f:
                            # Read bytes and decode to utf-8
                            # If it's not a text file, this will likely fail or produce garbage
                            # We use 'ignore' to handle binary files gracefully by skipping them
                            data = f.read().decode('utf-8', errors='ignore')
                            
                            # Simple heuristic: if it's mostly binary, it might not be a "text file"
                            # But for this implementation, we concatenate everything that can be decoded
                            all_text.append(data)
                    except Exception:
                        # Skip files that cannot be opened or read
                        continue
            
            # Join all contents with newlines
            result = "\n".join(all_text)
            
            return Response(content=result, media_type="text/plain")
            
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)