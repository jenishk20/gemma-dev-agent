const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 5000;

// Configure multer for temporary file storage
const upload = multer({ dest: 'uploads/' });

app.post('/concatenate', upload.array('files'), async (req, res) => {
    const files = req.files;

    if (!files || files.length === 0) {
        return res.status(400).json({ error: "Invalid input or missing files." });
    }

    // Create a unique session directory to avoid collisions between concurrent requests
    const requestId = uuidv4();
    const workDir = path.join(__dirname, 'temp', requestId);
    
    try {
        if (!fs.existsSync(workDir)) {
            fs.mkdirSync(workDir, { recursive: true });
        }

        // Move uploaded files to the session directory and keep track of paths
        const pdfPaths = [];
        for (const file of files) {
            const targetPath = path.join(workDir, `${file.filename}.pdf`);
            fs.renameSync(file.path, targetPath);
            pdfPaths.push(targetPath);
        }

        const outputFileName = `concatenated_${requestId}.pdf`;
        const outputPath = path.join(workDir, outputFileName);

        // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
        const command = `pdfunite ${pdfPaths.map(p => `"${p}"`).join(' ')} "${outputPath}"`;

        exec(command, (error) => {
            if (error) {
                console.error(`Execution error: ${error}`);
                return res.status(500).json({ error: "An error occurred while processing the files." });
            }

            // Send the resulting PDF file
            res.contentType('application/pdf');
            const fileStream = fs.createReadStream(outputPath);
            
            fileStream.pipe(res);

            // Cleanup files after the response is sent
            res.on('finish', () => {
                fs.rmSync(workDir, { recursive: true, force: true });
            });
        });

    } catch (err) {
        console.error(`Server error: ${err}`);
        res.status(500).json({ error: "An error occurred while processing the files." });
    }
});

// Ensure temp directory exists
const tempDir = path.join(__dirname, 'temp');
if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir);
}

app.listen(port, '0.0.0.0', () => {
    console.log(`PDF Concatenation Service listening on port ${port}`);
});