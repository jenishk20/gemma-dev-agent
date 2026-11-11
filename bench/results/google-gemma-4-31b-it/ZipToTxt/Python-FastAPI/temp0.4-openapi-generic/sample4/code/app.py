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
    # Validate that the uploaded file is a zip file based on content type or filename
    if not file.filename.endswith('.zip') and file.content_type != 'application/zip':
        raise HTTPException(status_code=400, detail="Invalid input: Please upload a .zip file")

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        
        combined_text = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Get list of files in the zip
            file_list = z.namelist()
            
            # To avoid ZipSlip/Path Traversal, we only iterate through the names 
            # and read the content without extracting to the filesystem.
            for filename in file_list:
                # We only process files (not directories)
                # We check if the file is a text file. 
                # In a real-world scenario, we might check magic numbers, 
                # but here we check for common text extensions or attempt to decode.
                if filename.endswith(('.txt', '.py', '.md', '.json', '.csv', '.html', '.css', '.js')):
                    try:
                        with z.open(filename) as f:
                            # Read bytes and decode to string
                            # Using 'utf-8' with 'ignore' to prevent crashing on binary files 
                            # that happen to have a text extension
                            text_content = f.read().decode('utf-8', errors='ignore')
                            combined_text.append(text_content)
                    except Exception:
                        # Skip files that cannot be read
                        continue

        if not combined_text:
            # If no text files were found, we return an empty string or a 400
            # Based on the schema, we return a string.
            return ""

        # Join all contents with a newline as a separator
        final_output = "\n".join(combined_text)
        return Response(content=final_output, media_type="text/plain")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file is not a valid zip archive")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)