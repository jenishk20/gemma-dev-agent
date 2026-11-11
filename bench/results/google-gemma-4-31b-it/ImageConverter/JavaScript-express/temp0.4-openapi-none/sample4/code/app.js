const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 5000;

// Configure multer for temporary file storage
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
    const workingDir = path.join(__dirname, 'tmp', requestId);
    
    try {
        if (!fs.existsSync(workingDir)) {
            fs.mkdirSync(workingDir, { recursive: true });
        }

        // Move uploaded files to working directory to maintain order and naming
        const imagePaths = files.map((file, index) => {
            const newPath = path.join(workingDir, `frame_${index}.png`);
            fs.renameSync(file.path, newPath);
            return newPath;
        });

        // Handle appendReverted logic
        let finalImagePaths = [...imagePaths];
        if (appendReverted === 'true' || appendReverted === true) {
            const reverted = [...imagePaths].reverse();
            finalImagePaths = [...imagePaths, ...reverted];
        }

        const outputGifPath = path.join(workingDir, 'result.gif');
        
        // Construct ImageMagick command
        // -delay is in ticks (1/100th of a second). 100ms = 10 ticks.
        const delayTicks = Math.round(parseInt(delay || 10) / 10);
        const sizeArg = `-resize ${targetSize}`;
        
        // Command: convert -delay 10 -resize 500x500 img1.png img2.png ... result.gif
        const cmd = `convert -delay ${delayTicks} ${sizeArg} ${finalImagePaths.join(' ')} ${outputGifPath}`;

        exec(cmd, (error, stdout, stderr) => {
            if (error) {
                console.error(`Exec error: ${error}`);
                return res.status(500).json({ error: 'ImageMagick conversion failed.' });
            }

            if (fs.existsSync(outputGifPath)) {
                res.setHeader('Content-Type', 'image/gif');
                res.sendFile(outputGifPath, (err) => {
                    // Cleanup after sending file
                    fs.rmSync(workingDir, { recursive: true, force: true });
                    if (err) {
                        console.error('Error sending file:', err);
                    }
                });
            } else {
                res.status(500).json({ error: 'GIF file was not created.' });
            }
        });

    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'Internal server error occurred.' });
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`GIF Creator API listening at http://0.0.0.0:${port}`);
});