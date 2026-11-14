const express = require('express');
const multer = require('multer');
const unzipper = require('unzipper');
const { Readable } = require('stream');

const app = express();
const port = 5000;

// Configure multer to store files in memory
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

/**
 * POST /convert
 * Converts a zip file to a single text file by concatenating 
 * the contents of all files inside the zip.
 */
app.post('/convert', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).send('No file uploaded.');
        }

        if (req.file.mimetype !== 'application/zip' && req.file.originalname.endsWith('.zip') === false) {
            return res.status(400).send('Uploaded file must be a zip archive.');
        }

        // Create a readable stream from the buffer
        const zipBuffer = Readable.from(req.file.buffer);
        
        let concatenatedText = '';
        
        // Use unzipper to parse the zip archive
        const directory = await unzipper.open(zipBuffer);
        
        // Iterate through files in the zip
        for (const entry of directory.files) {
            // We only process files (not directories)
            if (entry.type === 'File') {
                const content = await entry.buffer();
                // Convert buffer to string (assuming UTF-8)
                concatenatedText += content.toString('utf8') + '\n';
            }
        }

        // Set content type to text/plain as per OpenAPI schema
        res.setHeader('Content-Type', 'text/plain');
        res.status(200).send(concatenatedText.trim());

    } catch (error) {
        console.error('Error processing zip file:', error);
        res.status(400).send('Invalid input or corrupted zip file.');
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`ZipToTxt server listening at http://0.0.0.0:${port}`);
});