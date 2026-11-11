const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const SONGS_DIR = '/var/songs';

app.use(express.json());

/**
 * POST /download
 * Retrieves a song from the server data directory and streams it to the client.
 */
app.post('/download', (req, res) => {
    const { filename } = req.body;

    // 400: Invalid input
    if (!filename || typeof filename !== 'string') {
        return res.status(400).send('Invalid input: filename is required and must be a string.');
    }

    // Security: Prevent Directory Traversal attacks
    // Ensure the filename does not contain path separators or ".."
    const sanitizedFilename = path.basename(filename);
    if (sanitizedFilename !== filename) {
        return res.status(400).send('Invalid filename format.');
    }

    const filePath = path.join(SONGS_DIR, sanitizedFilename);

    // Check if file exists
    if (!fs.existsSync(filePath)) {
        return res.status(404).send('File does not exist.');
    }

    // Set the content type to audio/mpeg as per OpenAPI spec
    res.setHeader('Content-Type', 'audio/mpeg');
    res.setHeader('Content-Disposition', `attachment; filename="${sanitizedFilename}"`);

    // Create a read stream to pipe the file content to the response
    const fileStream = fs.createReadStream(filePath);

    fileStream.on('error', (error) => {
        console.error(error);
        if (!res.headersSent) {
            res.status(500).send('Internal server error while streaming file.');
        }
    });

    fileStream.pipe(res);
});

app.listen(PORT, HOST, () => {
    console.log(`SongDownloader API running at http://${HOST}:${PORT}`);
});