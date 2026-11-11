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
        if (pdfFiles.length !== files.length) {
            // Cleanup uploaded files if validation fails
            files.forEach(file => fs.unlinkSync(file.path));
            return res.status(400).json({ error: "All uploaded files must be PDFs." });
        }

        const requestId = uuidv4();
        const outputFileName = `concatenated_${requestId}.pdf`;
        const outputPath = path.join('uploads', outputFileName);
        
        // Construct the command: pdfunite file1 file2 ... output
        const inputPaths = files.map(file => `"${file.path}"`).join(' ');
        const command = `pdfunite ${inputPaths} "${outputPath}"`;

        exec(command, (error) => {
            if (error) {
                console.error(`Execution error: ${error}`);
                // Cleanup
                files.forEach(file => fs.unlinkSync(file.path));
                if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
                
                return res.status(500).json({ error: "An error occurred while processing the files." });
            }

            // Send the resulting PDF file
            res.contentType('application/pdf');
            res.sendFile(outputPath, (err) => {
                // Cleanup after sending the file
                files.forEach(file => fs.unlinkSync(file.path));
                fs.unlinkSync(outputPath);
                if (err) {
                    console.error(`Error sending file: ${err}`);
                }
            });
        });

    } catch (err) {
        console.error(`Server error: ${err}`);
        res.status(500).json({ error: "An error occurred while processing the files." });
    }
});

// Ensure uploads directory exists
const uploadDir = 'uploads';
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

app.listen(port, '0.0.0.0', () => {
    console.log(`PDF Concatenation Service listening at http://0.0.0.0:${port}`);
});