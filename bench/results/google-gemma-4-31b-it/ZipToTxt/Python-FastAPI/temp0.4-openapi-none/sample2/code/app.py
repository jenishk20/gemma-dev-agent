import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
import uvicorn

app = FastAPI(
    title="ZipToTxt",
    description="A simple webapp API for converting zip files into a single text file.",
    version="1.0.11"
)

@app.post("/convert", summary="Convert a zip file to a text file")
async def convert_zip_to_txt(file: UploadFile = File(...)):
    """
    Convert a zip file into a single text file, concatenating the contents of all text files in the zip.
    """
    # Validate that the uploaded file is actually a zip file based on content type or extension
    if not file.filename.endswith('.zip'):
        # We check the extension as a basic validation, but zipfile.is_zipfile is more robust
        pass

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)

        # Check if it's a valid zip file
        if not zipfile.is_zipfile(zip_buffer):
            raise HTTPException(status_code=400, detail="Invalid input: The uploaded file is not a valid zip archive.")

        # Reset buffer position to start
        zip_buffer.seek(0)
        
        combined_text = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Get list of all files in the zip
            file_list = z.namelist()
            
            for file_name in file_list:
                # We only process files that are likely text files. 
                # Since the requirement is "contents of all text files", 
                # we filter by common text extensions or attempt to read.
                # Standard approach: check if it's not a directory.
                info = z.getinfo(file_name)
                if info.is_dir():
                    continue
                
                # We attempt to read the file. If it's binary, it might crash or produce garbage.
                # To be safe and follow "text files", we filter by .txt or attempt decoding.
                try:
                    with z.open(file_name) as f:
                        # Read bytes and decode to utf-8
                        content = f.read().decode('utf-8')
                        combined_text.append(content)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that aren't valid UTF-8 text files
                    continue

        # Join all extracted text with newlines
        final_output = "\n".join(combined_text)
        
        # Return as plain text
        return Response(content=final_output, media_type="text/plain")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)