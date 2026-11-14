const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const multer = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();
const port = 5000;

// Database setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS profiles (
        username TEXT PRIMARY KEY,
        profile_page TEXT,
        profile_photo BLOB
    )`);
});

// Multer setup for multipart/form-data
// We use memoryStorage because we are saving the binary data directly into SQLite
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

/**
 * POST /add_profile
 * Adds a new user profile with HTML content and a PNG image.
 */
app.post('/add_profile', upload.single('profile_photo'), (req, res) => {
    const { username, profile_page } = req.body;
    const profile_photo = req.file ? req.file.buffer : null;

    if (!username || !profile_page) {
        return res.status(400).send('Invalid input: username and profile_page are required.');
    }

    if (!profile_photo) {
        return res.status(400).send('Invalid input: profile_photo is required.');
    }

    // Validate that the file is a PNG (basic check)
    if (req.file.mimetype !== 'image/png') {
        return res.status(400).send('Invalid input: profile_photo must be a PNG image.');
    }

    const query = `INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)`;
    db.run(query, [username, profile_page, profile_photo], function(err) {
        if (err) {
            if (err.message.includes('UNIQUE constraint failed')) {
                return res.status(403).send('Profile already exists, creation forbidden');
            }
            return res.status(500).send('Internal Server Error');
        }
        res.status(201).send('Profile created successfully');
    });
});

/**
 * GET /profile/{username}
 * Retrieves the HTML content for a given username.
 */
app.get('/profile/:username', (req, res) => {
    const username = req.params.username;
    const query = `SELECT profile_page FROM profiles WHERE username = ?`;

    db.get(query, [username], (err, row) => {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }
        if (!row) {
            return res.status(404).send('Profile not found');
        }
        res.setHeader('Content-Type', 'text/html');
        res.send(row.profile_page);
    });
});

/**
 * GET /profile-photo/{username}
 * Retrieves the PNG profile picture for a given username.
 */
app.get('/profile-photo/:username', (req, res) => {
    const username = req.params.username;
    const query = `SELECT profile_photo FROM profiles WHERE username = ?`;

    db.get(query, [username], (err, row) => {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }
        if (!row || !row.profile_photo) {
            return res.status(404).send('Profile photo not found');
        }
        res.setHeader('Content-Type', 'image/png');
        res.send(row.profile_photo);
    });
});

// Start server
app.listen(port, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${port}`);
});