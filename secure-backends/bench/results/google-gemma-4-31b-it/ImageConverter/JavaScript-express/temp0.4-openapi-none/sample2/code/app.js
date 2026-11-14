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
    try {
        const { targetSize, delay, appendReverted } = req.body;
        const files = req.files;

        // Validation
        if (!files || files.length === 0) {
            return res.status(400).json({ error: 'No images provided' });
        }
        if (!targetSize) {
            return res.status(400).json({ error: 'targetSize is required' });
        }

        const frameDelay = delay || 10;
        const shouldRevert = appendReverted === 'true' || appendReverted === true;
        
        // Create a unique session folder for this request
        const requestId = uuidv4();
        const workDir = path.join(__dirname, 'temp', requestId);
        if (!fs.existsSync(workDir)) {
            fs.mkdirSync(workDir, { recursive: true });
        }

        // Move uploaded files to workDir and keep track of paths
        const imagePaths = [];
        files.forEach((file, index) => {
            const ext = path.extname(file.originalname) || '.tmp';
            const destPath = path.join(workDir, `frame_${index}${ext}`);
            fs.renameSync(file.path, destPath);
            imagePaths.push(destPath);
        });

        // Handle the "appendReverted" logic (Ping-pong effect)
        let finalImageList = [...imagePaths];
        if (shouldRevert && imagePaths.length > 1) {
            const reverted = [...imagePaths].reverse().slice(1, -1);
            finalImageList = finalImageList.concat(reverted);
        }

        const outputGifPath = path.join(workDir, 'result.gif');
        
        // Construct ImageMagick command
        // -delay: time between frames (1/100th of a second in IM, but the schema asks for ms)
        // Note: ImageMagick -delay is in ticks (usually 1/100s). 
        // To get ms, we divide by 10.
        const imDelay = Math.round(frameDelay / 10);
        
        // Command: convert -delay X -resize Y -loop 0 input1 input2 ... output.gif
        const imagesString = finalImageList.join(' ');
        const cmd = `convert -delay ${imDelay} -resize ${targetSize} -loop 0 ${imagesString} ${outputGifPath}`;

        exec(cmd, (error) => {
            if (error) {
                console.error(`Exec error: ${error}`);
                // Cleanup
                fs.rmSync(workDir, { recursive: true, force: true });
                return res.status(500).json({ error: 'Failed to process GIF' });
            }

            // Send the file
            res.sendFile(outputGifPath, (err) => {
                // Cleanup after sending
                fs.rmSync(workDir, { recursive: true, force: true });
                if (err) {
                    console.error('Error sending file:', err);
                }
            });
        });

    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// Ensure temp directory exists
if (!fs.existsSync('temp')) {
    fs.mkdirSync('temp');
}
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(port, '0.0.0.0', () => {
    console.log(`GIF Creator API listening at http://0.0.0.0:${port}`);
});