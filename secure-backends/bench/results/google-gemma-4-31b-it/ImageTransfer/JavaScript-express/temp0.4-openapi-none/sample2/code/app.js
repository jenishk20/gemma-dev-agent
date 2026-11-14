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

// Initialize SQLite Database to store image metadata (mimetype and filename)
const db = new sqlite3.Database(':memory:');
db.serialize(() => {
    db.run("CREATE TABLE images (id TEXT PRIMARY KEY, filename TEXT, mimetype TEXT)");
});

// Multer configuration for file storage
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueId = uuidv4();
        cb(null, `${uniqueId}${path.extname(file.originalname)}`);
    }
});

const upload = multer({ storage: storage });

app.use(express.json());

/**
 * POST /upload
 * Uploads an image and returns a shareable ID.
 */
app.post('/upload', upload.single('file'), (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        const imageId = uuidv4();
        const filename = req.file.filename;
        const mimetype = req.file.mimetype;

        const stmt = db.prepare("INSERT INTO images VALUES (?, ?, ?)");
        stmt.run(imageId, filename, mimetype, (err) => {
            if (err) {
                return res.status(500).json({ error: 'Database error occurred' });
            }
            res.status(200).json({ id: imageId });
        });
        stmt.finalize();
    } catch (error) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

/**
 * GET /images/{imageId}
 * Serves the image file to the browser.
 */
app.get('/images/:imageId', (req, res) => {
    const imageId = req.params.imageId;

    db.get("SELECT filename, mimetype FROM images WHERE id = ?", [imageId], (err, row) => {
        if (err) {
            return res.status(500).json({ error: 'Internal server error' });
        }
        if (!row) {
            return res.status(404).json({ error: 'Image not found' });
        }

        const filePath = path.join(uploadDir, row.filename);

        if (!fs.existsSync(filePath)) {
            return res.status(404).json({ error: 'Image file missing from storage' });
        }

        // Set Content-Type to ensure browser views the image instead of downloading
        res.setHeader('Content-Type', row.mimetype);
        // Content-Disposition: inline tells the browser to try and render it in-page
        res.setHeader('Content-Disposition', `inline; filename="${row.filename}"`);
        
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
    console.log(`Server running on http://0.0.0.0:${port}`);
});