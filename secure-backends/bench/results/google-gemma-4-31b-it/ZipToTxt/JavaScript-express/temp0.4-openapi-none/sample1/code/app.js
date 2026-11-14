const express = require('express');
const multer = require('multer');
const unzipper = require('unzipper');
const app = express();
const port = 5000;

// Configure multer to handle file uploads in memory
const upload = multer({ storage: multer.memoryStorage() });

/**
 * POST /convert
 * Converts a zip file to a single text file by concatenating the contents
 * of all files within the zip.
 */
app.post('/convert', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).send('No file uploaded.');
        }

        if (req.file.mimetype !== 'application/zip' && req.file.originalname.endsWith('.zip') === false) {
            // Basic check for zip format
            return res.status(400).send('Invalid input: Please upload a .zip file.');
        }

        // Create a buffer from the uploaded file
        const zipBuffer = req.file.buffer;
        
        // Open the zip archive
        const directory = await unzipper.Open.buffer(zipBuffer);
        
        let combinedText = '';

        // Iterate through all files in the zip
        for (const file of directory.files) {
            // We only process files (ignore directories)
            if (!file.type === 'Directory') {
                // Extract the content of the file as a buffer
                const contentBuffer = await file.buffer();
                // Convert buffer to string (UTF-8) and append to result
                combinedText += contentBuffer.toString('utf8') + '\n';
            }
        }

        // Set response header to text/plain as per OpenAPI spec
        res.setHeader('Content-Type', 'text/plain');
        res.status(200).send(combinedText.trim());

    } catch (error) {
        console.error('Conversion error:', error);
        res.status(400).send('Invalid input: Failed to process zip file.');
    }
});

// Start the server on 0.0.0.0:5000
app.listen(port, '0.0.0.0', () => {
    console.log(`ZipToTxt API running on http://0.0.0.0:${port}`);
});