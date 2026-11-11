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

app.post('/concatenate', upload.array('files'), async (req, res) => {
    try {
        const files = req.files;

        if (!files || files.length === 0) {
            return res.status(400).json({ error: "Invalid input or missing files." });
        }

        // Validate that all uploaded files are PDFs (basic check)
        const pdfFiles = files.filter(file => file.originalname.toLowerCase().endsWith('.pdf'));
        if (pdfFiles.length === 0) {
            // Cleanup any uploaded files if none are PDFs
            files.forEach(file => fs.unlinkSync(file.path));
            return res.status(400).json({ error: "No PDF files provided." });
        }

        const requestId = uuidv4();
        const inputPaths = pdfFiles.map(file => file.path);
        const outputFileName = `concatenated_${requestId}.pdf`;
        const outputPath = path.join('uploads', outputFileName);

        // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
        const command = `pdfunite ${inputPaths.join(' ')} ${outputPath}`;

        exec(command, (error) => {
            // Cleanup input files immediately after execution attempt
            inputPaths.forEach(path => {
                if (fs.existsSync(path)) fs.unlinkSync(path);
            });

            if (error) {
                console.error(`Execution error: ${error}`);
                return res.status(500).json({ error: "An error occurred while processing the files." });
            }

            // Check if output file was created
            if (fs.existsSync(outputPath)) {
                res.setHeader('Content-Type', 'application/pdf');
                res.sendFile(outputPath, (err) => {
                    // Delete the concatenated file after sending it to the client
                    if (fs.existsSync(outputPath)) {
                        fs.unlinkSync(outputPath);
                    }
                    if (err) {
                        console.error(`Error sending file: ${err}`);
                    }
                });
            } else {
                res.status(500).json({ error: "Failed to generate concatenated PDF." });
            }
        });

    } catch (err) {
        console.error(`Server error: ${err}`);
        res.status(500).json({ error: "An error occurred while processing the files." });
    }
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(port, '0.0.0.0', () => {
    console.log(`PDF Concatenation Service listening at http://0.0.0.0:${port}`);
});