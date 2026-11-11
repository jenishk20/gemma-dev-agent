const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const uuid = require('uuid');

const execPromise = promisify(exec);
const app = express();
const port = 5000;

// Configure multer for temporary file uploads
const upload = multer({ dest: 'uploads/' });

app.post('/extract', upload.single('video'), async (req, res) => {
    const { frameNumber, videoFileName } = req.body;
    const videoFile = req.file;

    if (!videoFile || frameNumber === undefined) {
        return res.status(400).json({ error: "Missing video file or frameNumber" });
    }

    const requestId = uuid.v4();
    const inputPath = videoFile.path;
    const outputPath = path.join('uploads', `${requestId}.png`);

    try {
        // ffmpeg command to extract a specific frame by index
        // -i: input file
        // -vf "select=not(mod(n,1))": select frames (this is a dummy filter to ensure we can use -vframes)
        // -vframes 1: output exactly one frame
        // Since ffmpeg's 'select' filter is complex for specific indices, 
        // we use the standard approach: seek to the frame index.
        // Note: frameNumber is 0-indexed.
        
        // Command: ffmpeg -i input.mp4 -vf "select=eq(n,FRAME_INDEX)" -vframes 1 output.png
        const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${parseInt(frameNumber)})" -vframes 1 "${outputPath}"`;
        
        await execPromise(command);

        if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
            throw new Error("Frame not found");
        }

        // Send the image file
        res.sendFile(outputPath, (err) => {
            // Cleanup files after sending
            try {
                if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
                if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
            } catch (cleanupErr) {
                console.error("Cleanup error:", cleanupErr);
            }
            if (err) {
                console.error("Error sending file:", err);
            }
        });

    } catch (error) {
        // Cleanup input file on failure
        if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
        if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

        res.status(404).json({
            error: `Frame at index ${frameNumber} could not be found.`
        });
    }
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(port, '0.0.0.0', () => {
    console.log(`FrameExtract server listening at http://0.0.0.0:${port}`);
});