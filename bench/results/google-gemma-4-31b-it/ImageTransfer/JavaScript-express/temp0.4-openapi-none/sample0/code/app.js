const express = require('express');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');
const sqlite3 = require('sqlite3').verbose();

const app = express();
const port = 5000;
const uploadDir = 'uploads';

// Ensure upload directory exists
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

// Database setup to store mapping between imageId and original filename/mimetype
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
        const uniqueId = uuidv4();
        // We store the file with the UUID as the name to avoid collisions
        cb(null, `${uniqueId}${path.extname(file.originalname)}`);
    }
});

const upload = multer({ storage: storage });

/**
 * POST /upload
 * Uploads an image and returns a shareable ID.
 */
app.post('/upload', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    const imageId = uuidv4();
    const { filename, mimetype } = req.file;

    db.run('INSERT INTO images (id, filename, mimetype) VALUES (?, ?, ?)', [imageId, filename, mimetype], (err) => {
        if (err) {
            return res.status(500).json({ error: 'Database error occurred' });
        }
        res.status(200).json({ id: imageId });
    });
});

/**
 * GET /images/{imageId}
 * Serves the image file with the correct mimetype to be viewed in browser.
 */
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
            return res.status(404).json({ error: 'Image file missing from storage' });
        }

        // Set Content-Type to the original mimetype so the browser renders it
        // We avoid Content-Disposition: attachment to ensure it is viewable and not downloaded
        res.setHeader('Content-Type', row.mimetype);
        res.sendFile(filePath);
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Image Upload and Share API listening at http://0.0.0.0:${port}`);
});