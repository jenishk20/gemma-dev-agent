const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = express();
const port = 5000;

// Configure multer for temporary file storage
const upload = multer({ dest: 'uploads/' });

app.post('/extract', upload.single('video'), async (req, res) => {
    try {
        const frameNumber = req.body.frameNumber;
        const videoFile = req.file;

        if (!videoFile || frameNumber === undefined) {
            return res.status(400).json({ error: 'Missing video file or frameNumber' });
        }

        const inputPath = videoFile.path;
        const outputPath = `uploads/frame_${Date.now()}.png`;

        // ffmpeg command to extract a specific frame by index
        // -i: input file
        // -vf "select=not(mod(n,1))": this is a placeholder, we use the specific index
        // The correct filter for a specific frame index is "select=eq(n,FRAME_INDEX)"
        // We then use -vframes 1 to ensure only one frame is output
        const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 "${outputPath}"`;

        try {
            await execPromise(command);

            // Check if the output file was actually created and has size > 0
            if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
                throw new Error('Frame not found');
            }

            // Send the image and then clean up files
            res.sendFile(outputPath, (err) => {
                // Cleanup: remove both video and extracted frame
                fs.unlinkSync(inputPath);
                if (fs.existsSync(outputPath)) {
                    fs.unlinkSync(outputPath);
                }
            });
        } catch (error) {
            // Cleanup input file if ffmpeg failed
            if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
            if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

            return res.status(404).json({ 
                error: `Frame at index ${frameNumber} could not be found.` 
            });
        }
    } catch (globalError) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(port, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${port}`);
});