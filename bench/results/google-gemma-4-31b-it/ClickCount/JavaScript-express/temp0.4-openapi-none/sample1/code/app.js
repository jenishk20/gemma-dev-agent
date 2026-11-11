const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const app = express();
const port = 5000;
const dbPath = path.join(__dirname, 'db.sqlite3');

app.use(express.json());

// Initialize Database
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('Error opening database:', err.message);
    } else {
        db.run(`CREATE TABLE IF NOT EXISTS clicks (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )`, (err) => {
            if (err) {
                console.error('Error creating table:', err.message);
            }
        });
    }
});

/**
 * POST /click
 * Register a user's click
 */
app.post('/click', (req, res) => {
    const id = uuidv4();
    const timestamp = new Date().toISOString();

    const query = `INSERT INTO clicks (id, timestamp) VALUES (?, ?)`;
    db.run(query, [id, timestamp], function(err) {
        if (err) {
            return res.status(400).json({ error: 'Invalid request' });
        }
        res.status(201).send();
    });
});

/**
 * GET /clicks
 * Retrieve clicks based on date and direction
 */
app.get('/clicks', (req, res) => {
    const { date, direction } = req.query;

    // Validation
    if (!date || !direction) {
        return res.status(400).json({ error: 'Missing required query parameters: date and direction' });
    }

    const validDirections = ['<', '>', '<=', '>='];
    if (!validDirections.includes(direction)) {
        return res.status(400).json({ error: 'Invalid direction. Must be one of: <, >, <=, >=' });
    }

    // Basic date format validation (YYYY-MM-DD)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        return res.status(400).json({ error: 'Invalid date format. Expected YYYY-MM-DD' });
    }

    // We use a parameterized query for the date, but the operator (direction) 
    // must be white-listed since SQL parameters cannot be used for operators.
    const query = `SELECT id, timestamp FROM clicks WHERE date(timestamp) ${direction} ?`;

    db.all(query, [date], (err, rows) => {
        if (err) {
            return res.status(400).json({ error: 'Database query error' });
        }

        if (!rows || rows.length === 0) {
            return res.status(404).json({ error: 'No clicks found' });
        }

        res.status(200).json(rows);
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Click Tracking API listening at http://0.0.0.0:${port}`);
});