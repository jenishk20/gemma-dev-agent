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

        if (req.file.mimetype !== 'application/zip' && !req.file.originalname.endsWith('.zip')) {
            return res.status(400).send('Invalid input: Please upload a zip file.');
        }

        let combinedText = '';
        
        // Create a directory from the buffer
        const directory = await unzipper.Open.buffer(req.file.buffer);

        // Iterate through files in the zip
        for (const file of directory.files) {
            // We only want to process files, not directories
            if (file.type === 'File') {
                // Read the content of the file
                const content = await file.buffer();
                combinedText += content.toString('utf8') + '\n';
            }
        }

        // Set response type to text/plain as per OpenAPI spec
        res.setHeader('Content-Type', 'text/plain');
        res.status(200).send(combinedText.trim());
    } catch (error) {
        console.error('Error processing zip file:', error);
        res.status(400).send('Invalid input: Failed to process zip file.');
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`ZipToTxt API listening at http://0.0.0.0:${port}`);
});