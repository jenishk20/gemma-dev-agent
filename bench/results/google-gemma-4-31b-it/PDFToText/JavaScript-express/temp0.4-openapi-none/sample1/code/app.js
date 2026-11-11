const express = require('express');
const multer = require('multer');
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 5000;

// Configure multer for file uploads
// We store files in a temporary directory to process them with pdftotext
const upload = multer({ 
    dest: 'uploads/',
    fileFilter: (req, file, cb) => {
        if (file.mimetype === 'application/pdf') {
            cb(null, true);
        } else {
            cb(new Error('Only PDF files are allowed'), false);
        }
    }
});

app.post('/convert', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    const inputPath = req.file.path;
    const outputFileName = `${uuidv4()}.txt`;
    const outputPath = path.join('uploads', outputFileName);

    // pdftotext <input-pdf> <output-text-file>
    execFile('pdftotext', [inputPath, outputPath], (error, stdout, stderr) => {
        // Clean up the uploaded PDF file immediately
        fs.unlink(inputPath, (err) => {
            if (err) console.error(`Error deleting input file: ${err}`);
        });

        if (error) {
            console.error(`Execution error: ${error}`);
            return res.status(500).json({ error: 'Conversion failed' });
        }

        // Read the generated text file
        fs.readFile(outputPath, 'utf8', (err, data) => {
            // Clean up the generated text file
            fs.unlink(outputPath, (err) => {
                if (err) console.error(`Error deleting output file: ${err}`);
            });

            if (err) {
                console.error(`Read error: ${err}`);
                return res.status(500).json({ error: 'Failed to read converted text' });
            }

            res.setHeader('Content-Type', 'text/plain');
            res.status(200).send(data);
        });
    });
});

// Handle multer errors (like file filter error)
app.use((err, req, res, next) => {
    if (err instanceof multer.MulterError || err.message === 'Only PDF files are allowed') {
        return res.status(400).json({ error: err.message });
    }
    next(err);
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(port, '0.0.0.0', () => {
    console.log(`PDF to Text Converter API listening at http://0.0.0.0:${port}`);
});