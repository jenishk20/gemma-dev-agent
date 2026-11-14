import zipfile
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="ZipToTxt", version="1.0.11")

@app.post(
    "/convert", 
    summary="Convert a zip file to a text file", 
    description="Convert a zip file into a single text file, concatenating the contents of all text files in the zip.",
    response_class=PlainTextResponse
)
async def convert_zip_to_txt(file: UploadFile = File(...)):
    # Validate that the uploaded file is actually a zip file
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid input: The uploaded file must be a .zip archive.")

    try:
        # Read the uploaded file into memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        
        combined_text = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Get list of all files in the zip
            file_list = z.namelist()
            
            # Filter for text files (based on .txt extension)
            # We iterate through the files and extract content if they are text files
            for filename in file_list:
                if filename.endswith('.txt'):
                    with z.open(filename) as f:
                        # Read bytes and decode to string
                        # Using errors='ignore' or 'replace' to handle potential encoding issues
                        text_content = f.read().decode('utf-8', errors='replace')
                        combined_text.append(text_content)
        
        if not combined_text:
            # If no .txt files were found, we return an empty string or a specific message
            # Based on the schema, we return the concatenated content.
            return ""

        # Join all text contents with a newline separator
        return "\n".join(combined_text)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid input: The file is not a valid zip archive.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)