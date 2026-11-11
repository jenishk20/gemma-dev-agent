import zipfile
import io
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import PlainTextResponse

app = FastAPI(title="ZipToTxt", description="A simple webapp API for converting zip files into a single text file.")

@app.post(
    "/convert", 
    summary="Convert a zip file to a text file", 
    description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.",
    response_class=PlainTextResponse
)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # Validate that the uploaded file is a zip file
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file must be a .zip archive.")

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        
        all_text = []
        
        with zipfile.ZipFile(zip_buffer) as z:
            # Get list of all files in the zip
            file_list = z.namelist()
            
            for file_name in file_list:
                # Security: Prevent ZipSlip/Path Traversal by ignoring directories 
                # and ensuring we only process files. 
                # zipfile.ZipFile.read() handles the extraction from the archive safely.
                info = z.getinfo(file_name)
                if info.is_dir():
                    continue
                
                try:
                    # Attempt to read the file content as text
                    # We use 'utf-8' as the standard encoding. 
                    # If it fails, we skip the file as it's likely binary.
                    with z.open(file_name) as f:
                        content = f.read().decode('utf-8')
                        all_text.append(content)
                except (UnicodeDecodeError, Exception):
                    # Skip files that are not valid text files
                    continue
        
        # Join all extracted text contents with a newline
        result_text = "\n".join(all_text)
        
        if not result_text and not all_text:
            # If no text files were found or they were all empty
            return ""
            
        return Response(content=result_text, media_type="text/plain")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file is not a valid zip archive.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    # Start the server on port 5000 and host 0.0.0.0
    uvicorn.run(app, host="0.0.0.0", port=5000)