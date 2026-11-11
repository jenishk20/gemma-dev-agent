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
 * Retrieves a song by filename and streams it to the client.
 */
app.post('/download', (req, res) => {
    const { filename } = req.body;

    // 400: Invalid input (filename missing or not a string)
    if (!filename || typeof filename !== 'string') {
        return res.status(400).send('Invalid input: filename is required.');
    }

    // Security: Prevent Directory Traversal attacks
    // Ensure the filename doesn't contain path segments like '../'
    const safeFilename = path.basename(filename);
    const filePath = path.join(SONGS_DIR, safeFilename);

    // Check if file exists
    if (!fs.existsSync(filePath)) {
        return res.status(404).send('File does not exist');
    }

    try {
        // Set the content type to audio/mpeg as per OpenAPI spec
        res.setHeader('Content-Type', 'audio/mpeg');
        res.setHeader('Content-Disposition', `attachment; filename="${safeFilename}"`);

        // Create a read stream and pipe it to the response object
        const fileStream = fs.createReadStream(filePath);
        
        fileStream.on('error', (err) => {
            console.error('Stream error:', err);
            if (!res.headersSent) {
                res.status(500).send('Internal Server Error');
            }
        });

        fileStream.pipe(res);
    } catch (error) {
        console.error('Server error:', error);
        res.status(500).send('Internal Server Error');
    }
});

app.listen(PORT, HOST, () => {
    console.log(`SongDownloader API running at http://${HOST}:${PORT}`);
});