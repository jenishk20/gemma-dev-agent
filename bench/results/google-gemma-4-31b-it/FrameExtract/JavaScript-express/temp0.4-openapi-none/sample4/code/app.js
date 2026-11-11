const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = express();
const upload = multer({ dest: 'uploads/' });

const PORT = 5000;
const HOST = '0.0.0.0';

app.post('/extract', upload.single('video'), async (req, res) => {
    try {
        const frameNumber = parseInt(req.body.frameNumber);
        const videoFile = req.file;

        if (!videoFile || isNaN(frameNumber)) {
            return res.status(400).json({ error: 'Missing video file or invalid frame number.' });
        }

        const inputPath = videoFile.path;
        const outputPath = `${inputPath}_frame${frameNumber}.png`;

        /**
         * ffmpeg command explanation:
         * -i: input file
         * -vf "select=eq(n\,${frameNumber})": selects the frame where the index equals frameNumber
         * -vframes 1: output exactly one frame
         * -f image2: output format as image
         */
        const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n\\,${frameNumber})" -vframes 1 -f image2 "${outputPath}"`;

        try {
            await execPromise(command);

            // Check if the output file was actually created and has size > 0
            if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
                throw new Error('Frame not found');
            }

            // Send the image file
            res.setHeader('Content-Type', 'image/png');
            res.sendFile(outputPath, (err) => {
                // Cleanup files after sending
                try { fs.unlinkSync(inputPath); } catch (e) {}
                try { fs.unlinkSync(outputPath); } catch (e) {}
            });

        } catch (error) {
            // Cleanup input file on failure
            try { fs.unlinkSync(inputPath); } catch (e) {}
            try { fs.unlinkSync(outputPath); } catch (e) {}
            
            return res.status(404).json({ 
                error: `Frame at index ${frameNumber} could not be found.` 
            });
        }
    } catch (globalError) {
        console.error(globalError);
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}/`);
});