const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const SONGS_DIR = '/var/songs';

// Middleware to parse JSON bodies
app.use(express.json());

/**
 * POST /download
 * Retrieves a song file from the server data directory and streams it to the client.
 */
app.post('/download', (req, res) => {
    const { filename } = req.body;

    // 400: Invalid input (missing filename)
    if (!filename || typeof filename !== 'string') {
        return res.status(400).send('Invalid input: filename is required and must be a string.');
    }

    // Security: Prevent Directory Traversal attacks
    // Ensure the filename does not contain path separators or ".."
    const sanitizedFilename = path.basename(filename);
    if (sanitizedFilename !== filename) {
        return res.status(400).send('Invalid filename provided.');
    }

    const filePath = path.join(SONGS_DIR, sanitizedFilename);

    // Check if file exists
    fs.access(filePath, fs.constants.F_OK, (err) => {
        if (err) {
            // 404: File does not exist
            return res.status(404).send('File does not exist');
        }

        // Set the correct content type for audio/mpeg as per OpenAPI schema
        res.setHeader('Content-Type', 'audio/mpeg');

        // Create a read stream to pipe the file content to the response
        const fileStream = fs.createReadStream(filePath);

        fileStream.on('error', (streamErr) => {
            console.error('Stream error:', streamErr);
            if (!res.headersSent) {
                res.status(500).send('An error occurred while streaming the file.');
            }
        });

        fileStream.pipe(res);
    });
});

app.listen(PORT, HOST, () => {
    console.log(`SongDownloader API running at http://${HOST}:${PORT}`);
});