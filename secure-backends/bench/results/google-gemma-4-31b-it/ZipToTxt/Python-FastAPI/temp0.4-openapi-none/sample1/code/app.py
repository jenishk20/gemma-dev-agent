import zipfile
import io
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import PlainTextResponse

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
    # Validate that the uploaded file is actually a zip file based on content type or filename
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file must be a .zip archive.")

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        
        combined_text = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Get a list of all files in the zip
            file_list = z.namelist()
            
            # Iterate through files and extract content if it's a text file
            # We define text files as those ending in .txt or files that can be decoded as utf-8
            for filename in file_list:
                # Skip directories
                if filename.endswith('/'):
                    continue
                
                try:
                    with z.open(filename) as f:
                        # Read bytes and attempt to decode as utf-8
                        data = f.read().decode('utf-8')
                        combined_text.append(data)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that are not valid text files (binary files)
                    continue
        
        # Join all extracted text contents with newlines
        result = "\n".join(combined_text)
        return Response(content=result, media_type="text/plain")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid input: The file is not a valid zip archive.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred during conversion: {str(e)}")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)