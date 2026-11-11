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
    const { frameNumber } = req.body;
    const videoFile = req.file;

    if (!videoFile || frameNumber === undefined) {
        return res.status(400).json({ error: 'Missing video file or frameNumber' });
    }

    const inputPath = videoFile.path;
    const outputPath = path.join('uploads', `${videoFile.filename}_frame.png`);

    try {
        // ffmpeg command to extract a specific frame by index
        // -i: input file
        // -vf "select=eq(n\,X)": select frame index X
        // -vframes 1: output exactly one frame
        const cmd = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 "${outputPath}"`;
        
        await execPromise(cmd);

        // Check if the output file was actually created (ffmpeg might not error if frame is out of range)
        if (!fs.existsSync(outputPath)) {
            throw new Error('Frame not found');
        }

        // Send the image file
        res.setHeader('Content-Type', 'image/png');
        res.sendFile(outputPath, (err) => {
            // Cleanup files after sending
            try {
                fs.unlinkSync(inputPath);
                fs.unlinkSync(outputPath);
            } catch (cleanupErr) {
                console.error('Cleanup error:', cleanupErr);
            }
            if (err) {
                console.error('SendFile error:', err);
            }
        });

    } catch (error) {
        // Cleanup input file on failure
        try {
            if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
            if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
        } catch (cleanupErr) {}

        res.status(404).json({ 
            error: `Frame at index ${frameNumber} could not be found.` 
        });
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${port}`);
});