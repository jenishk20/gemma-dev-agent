const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5000;
const SONGS_DIRECTORY = '/var/songs';

app.use(express.json());

/**
 * POST /download
 * Retrieves a song by filename and streams it to the client.
 */
app.post('/download', (req, res) => {
    const { filename } = req.body;

    // 400: Invalid input - check if filename is provided and is a string
    if (!filename || typeof filename !== 'string') {
        return res.status(400).send('Invalid input: filename is required.');
    }

    // Security: Prevent directory traversal attacks by extracting only the base name
    const safeFilename = path.basename(filename);
    const filePath = path.join(SONGS_DIRECTORY, safeFilename);

    // Check if file exists
    if (!fs.existsSync(filePath)) {
        return res.status(404).send('File does not exist');
    }

    // Set the correct content type for MP3 streaming
    res.setHeader('Content-Type', 'audio/mpeg');

    // Create a read stream to pipe the file content to the response
    const fileStream = fs.createReadStream(filePath);

    fileStream.on('error', (err) => {
        console.error(`Stream error: ${err.message}`);
        if (!res.headersSent) {
            res.status(500).send('Internal server error while streaming file');
        }
    });

    fileStream.pipe(res);
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`SongDownloader API running on http://0.0.0.0:${PORT}`);
});