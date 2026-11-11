const express = require('express');
const multer = require('multer');
const unzipper = require('unzipper');
const app = express();

// Configure multer to handle file uploads in memory
const upload = multer({ storage: multer.memoryStorage() });

/**
 * POST /convert
 * Converts a zip file into a single text file by concatenating 
 * the contents of all files within the zip.
 */
app.post('/convert', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).send('No file uploaded.');
        }

        // The zip file is stored in req.file.buffer
        const zipBuffer = req.file.buffer;
        
        // Create a directory-like stream from the buffer
        const directory = await unzipper.Open.buffer(zipBuffer);
        
        let combinedText = '';

        // Iterate through all files in the zip archive
        for (const file of directory.files) {
            // We only process files (skip directories)
            if (file.type === 'File') {
                // Extract the content of the file as a buffer
                const contentBuffer = await file.buffer();
                // Convert buffer to string and append to the result
                combinedText += contentBuffer.toString('utf8') + '\n';
            }
        }

        // Set content type to text/plain as per OpenAPI spec
        res.setHeader('Content-Type', 'text/plain');
        res.status(200).send(combinedText.trim());
        
    } catch (error) {
        console.error('Error processing zip file:', error);
        res.status(400).send('Invalid input: Failed to process zip file.');
    }
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`ZipToTxt server running at http://${HOST}:${PORT}`);
});