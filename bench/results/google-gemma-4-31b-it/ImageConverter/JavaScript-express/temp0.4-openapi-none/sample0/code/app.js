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
    const outputGif = path.join(tempDir, 'result.gif');

    try {
        // Create temp directory
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }

        // Prepare list of input files
        let inputFiles = files.map(f => f.path);

        // Handle appendReverted: duplicate images in reverse order
        if (appendReverted === 'true' || appendReverted === true) {
            const reversed = [...inputFiles].reverse();
            // To avoid a double frame at the peak, we usually skip the first and last
            // but for a simple implementation, we just append the reverse.
            inputFiles = [...inputFiles, ...reversed];
        }

        // ImageMagick command construction
        // -delay is in 1/100ths of a second. 100ms = 10
        const imDelay = (parseInt(delay) || 10) / 10; 
        const geometry = targetSize; // e.g., "500x500"

        // Command: convert -delay 10 -resize 500x500 img1.jpg img2.jpg result.gif
        const cmd = `convert -delay ${imDelay} -resize ${geometry} ${inputFiles.join(' ')} ${outputGif}`;

        await execPromise(cmd);

        // Send the file
        res.contentType('image/gif');
        res.sendFile(outputGif, (err) => {
            // Cleanup after sending
            cleanup(tempDir);
        });

    } catch (error) {
        console.error(error);
        cleanup(tempDir);
        res.status(500).json({ error: 'Internal Server Error during GIF creation' });
    }
});

function cleanup(dir) {
    try {
        if (fs.existsSync(dir)) {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    } catch (e) {
        console.error('Cleanup error:', e);
    }
}

// Middleware to clean up multer's default upload folder periodically or on request
// For this specific app, we clean up the specific request folder in the response callback.
// However, we should also clean up the initial multer uploads.
app.use((req, res, next) => {
    next();
});

// Handle multer's temporary files cleanup
// Since multer stores files in 'uploads/', we should delete them after the process.
// We'll wrap the logic in the route to delete the specific files uploaded.
const originalPost = app.post.bind(app);
app.post = (path, ...args) => {
    const originalHandler = args[args.length - 1];
    const wrappedHandler = async (req, res, next) => {
        await originalHandler(req, res, next);
        if (req.files) {
            req.files.forEach(file => {
                fs.unlink(file.path, () => {});
            });
        }
    };
    return originalPost(path, ...args.slice(0, -1), wrappedHandler);
};

// Re-implementing the route without the wrapper for clarity since I modified app.post
// Let's just use a standard approach.
app.post('/create-gif', upload.array('images'), async (req, res) => {
    const { targetSize, delay, appendReverted } = req.body;
    const files = req.files;

    if (!files || files.length === 0) return res.status(400).json({ error: 'images are required' });
    if (!targetSize) return res.status(400).json({ error: 'targetSize is required' });

    const requestId = uuidv4();
    const tempDir = path.join(__dirname, 'temp', requestId);
    const outputGif = path.join(tempDir, 'result.gif');

    try {
        if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

        let inputFiles = files.map(f => f.path);
        if (appendReverted === 'true' || appendReverted === true) {
            inputFiles = [...inputFiles, ...[...inputFiles].reverse()];
        }

        const imDelay = (parseInt(delay) || 10) / 10;
        const cmd = `convert -delay ${imDelay} -resize ${targetSize} ${inputFiles.join(' ')} ${outputGif}`;

        await execPromise(cmd);

        res.contentType('image/gif');
        res.sendFile(outputGif, () => {
            cleanup(tempDir);
            files.forEach(f => fs.unlink(f.path, () => {}));
        });
    } catch (error) {
        cleanup(tempDir);
        files.forEach(f => fs.unlink(f.path, () => {}));
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`GIF Creator API listening at http://0.0.0.0:${port}`);
});