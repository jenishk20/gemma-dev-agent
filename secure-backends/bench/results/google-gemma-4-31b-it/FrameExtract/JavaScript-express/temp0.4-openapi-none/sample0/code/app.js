const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = express();
const port = 5000;

// Configure multer for temporary file storage
const upload = multer({ dest: 'uploads/' });

app.post('/extract', upload.single('video'), async (req, res) => {
    const { frameNumber, videoFileName } = req.body;
    const videoFile = req.file;

    if (!videoFile || !frameNumber) {
        return res.status(400).json({ error: "Missing video file or frameNumber" });
    }

    const inputPath = videoFile.path;
    const outputPath = path.join('uploads', `${Date.now()}_frame.png`);

    try {
        // ffmpeg command to extract a specific frame by index
        // -i: input file
        // -vf "select=eq(n\,X)": selects the frame where index n equals X
        // -vframes 1: output only one frame
        const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n\\,${frameNumber})" -vframes 1 "${outputPath}"`;
        
        await execPromise(command);

        // Check if the output file was actually created and has size > 0
        if (fs.existsSync(outputPath) && fs.statSync(outputPath).size > 0) {
            res.setHeader('Content-Type', 'image/png');
            res.sendFile(outputPath, (err) => {
                // Cleanup files after sending
                fs.unlink(inputPath, () => {});
                fs.unlink(outputPath, () => {});
                if (err) {
                    console.error("Error sending file:", err);
                }
            });
        } else {
            throw new Error("Frame not found");
        }
    } catch (error) {
        // Cleanup input file on failure
        fs.unlink(inputPath, () => {});
        if (fs.existsSync(outputPath)) fs.unlink(outputPath, () => {});

        res.status(404).json({
            error: `Frame at index ${frameNumber} could not be found.`
        });
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${port}`);
});