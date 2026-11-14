const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 5000;

// Configure Multer for temporary file storage
const upload = multer({ dest: 'uploads/' });

app.post('/create-gif', upload.array('images'), async (req, res) => {
    const { targetSize, delay, appendReverted } = req.body;
    const files = req.files;

    // Validation
    if (!files || files.length === 0) {
        return res.status(400).json({ error: 'No images provided.' });
    }
    if (!targetSize) {
        return res.status(400).json({ error: 'targetSize is required.' });
    }

    const requestId = uuidv4();
    const tempDir = path.join(__dirname, 'temp', requestId);
    const outputGif = path.join(tempDir, 'result.gif');

    try {
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }

        // Extract paths of uploaded files
        let imagePaths = files.map(f => f.path);

        // Handle appendReverted logic
        if (appendReverted === 'true' || appendReverted === true) {
            const reversed = [...imagePaths].reverse();
            imagePaths = [...imagePaths, ...reversed];
        }

        // Parse delay (default to 10 if not provided)
        const frameDelay = delay || 10;

        // ImageMagick 'convert' command construction
        // -delay: time between frames (1/100th of a second for GIF)
        // -resize: target size
        // -loop 0: infinite loop
        const delayValue = Math.floor(frameDelay / 10); 
        const cmd = `convert -delay ${delayValue} -loop 0 ${imagePaths.join(' ')} -resize ${targetSize} ${outputGif}`;

        exec(cmd, (error, stdout, stderr) => {
            if (error) {
                console.error(`Exec error: ${error}`);
                return res.status(500).json({ error: 'ImageMagick conversion failed.' });
            }

            // Send the resulting GIF file
            res.setHeader('Content-Type', 'image/gif');
            res.sendFile(outputGif, (err) => {
                // Cleanup files after sending
                cleanup(tempDir, files);
                if (err) {
                    console.error(`SendFile error: ${err}`);
                }
            });
        });

    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'Internal server error occurred.' });
    }
});

function cleanup(tempDir, uploadedFiles) {
    // Delete uploaded multer files
    uploadedFiles.forEach(file => {
        try { fs.unlinkSync(file.path); } catch (e) {}
    });
    // Delete the temp directory and the generated gif
    try {
        fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (e) {
        console.error('Cleanup error:', e);
    }
}

app.listen(port, '0.0.0.0', () => {
    console.log(`GIF Creator API listening at http://0.0.0.0:${port}`);
});