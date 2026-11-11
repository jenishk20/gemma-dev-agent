const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 5000;

// Configure multer for file uploads
// Files are stored temporarily in the 'uploads' directory
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueName = `${uuidv4()}${path.extname(file.originalname)}`;
        cb(null, uniqueName);
    }
});

const upload = multer({ 
    storage: storage,
    fileFilter: (req, file, cb) => {
        if (file.mimetype === 'application/pdf') {
            cb(null, true);
        } else {
            cb(new Error('Only PDF files are allowed'), false);
        }
    }
});

/**
 * POST /convert
 * Extracts text from a PDF file using the pdftotext utility.
 */
app.post('/convert', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    const inputPath = req.file.path;
    const outputPath = `${inputPath}.txt`;

    // pdftotext [input-file] [output-file]
    // We use exec to run the system command installed via poppler-utils
    exec(`pdftotext "${inputPath}" "${outputPath}"`, (error) => {
        if (error) {
            // Cleanup input file before returning error
            if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
            return res.status(500).json({ error: 'Conversion failed: ' + error.message });
        }

        fs.readFile(outputPath, 'utf8', (readError, data) => {
            // Cleanup both files
            try {
                if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
                if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
            } catch (cleanupError) {
                console.error('Cleanup error:', cleanupError);
            }

            if (readError) {
                return res.status(500).json({ error: 'Failed to read extracted text' });
            }

            // Return as plain text as per OpenAPI schema
            res.setHeader('Content-Type', 'text/plain');
            res.status(200).send(data);
        });
    });
});

// Global error handler for multer errors
app.use((err, req, res, next) => {
    if (err instanceof multer.MulterError || err.message === 'Only PDF files are allowed') {
        return res.status(400).json({ error: err.message });
    }
    res.status(500).json({ error: 'Internal Server Error' });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`PDF to Text Converter API listening at http://0.0.0.0:${port}`);
});