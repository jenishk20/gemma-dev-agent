const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = express();
const port = 5000;

// Configure multer for temporary file storage
const upload = multer({ dest: 'uploads/' });

app.post('/create-gif', upload.array('images'), async (req, res) => {
    const { targetSize, delay, appendReverted } = req.body;
    const files = req.files;

    // Validation
    if (!files || files.length === 0) {
        return res.status(400).json({ error: 'images are required' });
    }
    if (!targetSize) {
        return res.status(400).json({ error: 'targetSize is required' });
    }

    const requestId = uuidv4();
    const tempDir = path.join(__dirname, 'temp', requestId);
    
    try {
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }

        // Move uploaded files to a specific request directory for easier processing
        const inputPaths = [];
        for (const file of files) {
            const newPath = path.join(tempDir, file.filename);
            fs.renameSync(file.path, newPath);
            inputPaths.push(newPath);
        }

        // Handle appendReverted logic
        let finalPaths = [...inputPaths];
        if (appendReverted === 'true' || appendReverted === true) {
            const reversed = [...inputPaths].reverse();
            finalPaths = [...inputPaths, ...reversed];
        }

        const outputGifPath = path.join(tempDir, 'output.gif');
        const frameDelay = delay || 10;
        
        // ImageMagick command construction:
        // -delay: delay between frames in ticks (1/100th of a second). 
        // The schema asks for milliseconds, so we divide by 10.
        const delayTicks = Math.round(parseInt(frameDelay) / 10);
        
        // Construct the list of files for the command
        const filesList = finalPaths.join(' ');
        
        // Command: convert -delay [ticks] -resize [size] [files] [output]
        // We use -resize to match targetSize (e.g., 500x500)
        const command = `convert -delay ${delayTicks} -resize ${targetSize} ${filesList} ${outputGifPath}`;

        await execPromise(command);

        // Send the resulting GIF
        res.contentType('image/gif');
        res.sendFile(outputGifPath, (err) => {
            // Cleanup after sending file
            fs.rmSync(tempDir, { recursive: true, force: true });
            if (err) {
                console.error('Error sending file:', err);
            }
        });

    } catch (error) {
        console.error('Processing error:', error);
        // Cleanup on failure
        if (fs.existsSync(tempDir)) {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
        
        // Cleanup any multer files that weren't moved
        if (files) {
            files.forEach(f => {
                if (fs.existsSync(f.path)) fs.unlinkSync(f.path);
            });
        }

        res.status(500).json({ error: 'Internal Server Error: ' + error.message });
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`GIF Creator API listening at http://0.0.0.0:${port}`);
});