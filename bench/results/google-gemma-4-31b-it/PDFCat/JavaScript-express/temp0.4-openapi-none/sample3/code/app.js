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
    const files = req.files;

    if (!files || files.length === 0) {
        return res.status(400).json({ error: "Invalid input or missing files." });
    }

    // Validate that all uploaded files are PDFs (basic check)
    const pdfFiles = files.filter(file => file.mimetype === 'application/pdf' || file.originalname.toLowerCase().endsWith('.pdf'));
    
    if (pdfFiles.length !== files.length) {
        // Cleanup any uploaded files if some were not PDFs
        files.forEach(file => fs.unlinkSync(file.path));
        return res.status(400).json({ error: "All uploaded files must be PDFs." });
    }

    const requestId = uuidv4();
    const outputFileName = `concatenated_${requestId}.pdf`;
    const outputPath = path.join('uploads', outputFileName);
    
    // Prepare the list of input files for the CLI command
    const inputPaths = pdfFiles.map(file => `"${file.path}"`).join(' ');
    const command = `pdfunite ${inputPaths} "${outputPath}"`;

    exec(command, (error) => {
        if (error) {
            console.error(`Execution error: ${error}`);
            
            // Cleanup input files
            files.forEach(file => {
                if (fs.existsSync(file.path)) fs.unlinkSync(file.path);
            });

            return res.status(500).json({ error: "An error occurred while processing the files." });
        }

        try {
            // Send the concatenated file
            res.setHeader('Content-Type', 'application/pdf');
            res.sendFile(outputPath, (err) => {
                // Cleanup both input and output files after sending
                files.forEach(file => {
                    if (fs.existsSync(file.path)) fs.unlinkSync(file.path);
                });
                if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
                
                if (err) {
                    console.error(`Error sending file: ${err}`);
                }
            });
        } catch (sendError) {
            res.status(500).json({ error: "An error occurred while sending the processed file." });
        }
    });
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(port, '0.0.0.0', () => {
    console.log(`PDF Concatenation Service listening at http://0.0.0.0:${port}`);
});