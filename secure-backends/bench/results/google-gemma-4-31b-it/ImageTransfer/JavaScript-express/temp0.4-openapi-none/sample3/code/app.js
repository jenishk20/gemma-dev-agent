const express = require('express');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');
const sqlite3 = require('sqlite3').verbose();

const app = express();
const port = 5000;

// Ensure uploads directory exists
const uploadDir = 'uploads';
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

// Database setup to store mapping of ID to original filename and mimetype
const db = new sqlite3.Database(':memory:');
db.serialize(() => {
    db.run(`CREATE TABLE images (
        id TEXT PRIMARY KEY, 
        filename TEXT, 
        mimetype TEXT
    )`);
});

// Multer configuration for file storage
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        // Use UUID for the physical file to avoid collisions
        const uniqueFilename = `${uuidv4()}${path.extname(file.originalname)}`;
        cb(null, uniqueFilename);
    }
});

const upload = multer({ storage: storage });

// POST /upload - Upload an image
app.post('/upload', upload.single('file'), (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        const imageId = uuidv4();
        const { filename, mimetype } = req.file;

        db.run('INSERT INTO images (id, filename, mimetype) VALUES (?, ?, ?)', 
            [imageId, filename, mimetype], 
            (err) => {
                if (err) {
                    return res.status(500).json({ error: 'Database error' });
                }
                res.status(200).json({ id: imageId });
            }
        );
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// GET /images/{imageId} - Share/View an image
app.get('/images/:imageId', (req, res) => {
    const imageId = req.params.imageId;

    db.get('SELECT filename, mimetype FROM images WHERE id = ?', [imageId], (err, row) => {
        if (err) {
            return res.status(500).json({ error: 'Internal server error' });
        }
        if (!row) {
            return res.status(404).json({ error: 'Image not found' });
        }

        const filePath = path.join(uploadDir, row.filename);
        
        // Check if file actually exists on disk
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({ error: 'Image file missing' });
        }

        // Set Content-Type to the original mimetype so the browser renders it
        // Content-Disposition is omitted or set to 'inline' to prevent download prompt
        res.setHeader('Content-Type', row.mimetype);
        res.setHeader('Content-Disposition', 'inline');
        
        res.sendFile(filePath, (err) => {
            if (err) {
                if (!res.headersSent) {
                    res.status(500).json({ error: 'Error sending file' });
                }
            }
        });
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${port}`);
});