const express = require('express');
const multer = require('multer');
const unzipper = require('unzipper');
const app = express();

// Configure multer to store files in memory for processing
const upload = multer({ storage: multer.memoryStorage() });

/**
 * POST /convert
 * Converts a zip file into a single text file by concatenating 
 * the contents of all files found within the zip.
 */
app.post('/convert', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).send('No file uploaded.');
        }

        if (req.file.mimetype !== 'application/zip' && req.file.originalname.split('.').pop() !== 'zip') {
            return res.status(400).send('Invalid input: Please upload a zip file.');
        }

        let concatenatedText = '';
        
        // Create a zip directory from the buffer
        const directory = await unzipper.Open.buffer(req.file.buffer);

        // Iterate through all files in the zip
        for (const file of directory.files) {
            // We process files that are not directories
            if (!file.folder) {
                // Read the file content as a string
                const content = await file.buffer();
                concatenatedText += content.toString('utf8') + '\n';
            }
        }

        res.setHeader('Content-Type', 'text/plain');
        res.status(200).send(concatenatedText.trim());
    } catch (error) {
        console.error('Error processing zip file:', error);
        res.status(400).send('Invalid input: Failed to process zip file.');
    }
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`ZipToTxt API running at http://${HOST}:${PORT}`);
});