const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const SONGS_DIR = '/var/songs';

app.use(express.json());

/**
 * POST /download
 * Retrieves a song file from the server data directory and streams it to the client.
 */
app.post('/download', (req, res) => {
    const { filename } = req.body;

    // 400: Invalid input (missing filename)
    if (!filename || typeof filename !== 'string') {
        return res.status(400).send('Invalid input: filename is required.');
    }

    // Security: Prevent Path Traversal attacks
    // Ensure the filename doesn't contain directory navigation characters
    const safeFilename = path.basename(filename);
    const filePath = path.join(SONGS_DIR, safeFilename);

    // Verify the file exists and is actually a file
    fs.access(filePath, fs.constants.F_OK, (err) => {
        if (err) {
            // 404: File does not exist
            return res.status(404).send('File does not exist.');
        }

        // Set the correct content type for audio/mpeg as per OpenAPI schema
        res.setHeader('Content-Type', 'audio/mpeg');
        res.setHeader('Content-Disposition', `attachment; filename="${safeFilename}"`);

        // Stream the file content to the response
        const fileStream = fs.createReadStream(filePath);
        
        fileStream.pipe(res);

        fileStream.on('error', (streamErr) => {
            console.error('Stream error:', streamErr);
            if (!res.headersSent) {
                res.status(500).send('Internal server error during streaming.');
            }
        });
    });
});

app.listen(PORT, HOST, () => {
    console.log(`SongDownloader API running at http://${HOST}:${PORT}`);
});