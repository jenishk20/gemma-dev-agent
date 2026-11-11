const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';

app.use(express.json());

// Initialize SQLite Database
const db = new sqlite3.Database('./db.sqlite3', (err) => {
    if (err) {
        console.error('Error opening database:', err.message);
    } else {
        console.log('Connected to the SQLite database.');
        db.run(`CREATE TABLE IF NOT EXISTS clicks (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )`);
    }
});

/**
 * POST /click
 * Registers a user click.
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
 * Retrieves clicks based on date and direction.
 * Query params: date (YYYY-MM-DD), direction (<, >, <=, >=)
 */
app.get('/clicks', (req, res) => {
    const { date, direction } = req.query;

    // Validation
    if (!date || !direction) {
        return res.status(400).json({ error: 'Missing required query parameters: date and direction' });
    }

    const allowedDirections = ['<', '>', '<=', '>='];
    if (!allowedDirections.includes(direction)) {
        return res.status(400).json({ error: 'Invalid direction. Allowed values: <, >, <=, >=' });
    }

    // Simple date format validation (YYYY-MM-DD)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        return res.status(400).json({ error: 'Invalid date format. Expected YYYY-MM-DD' });
    }

    // SQLite allows comparing ISO strings. 
    // Since the schema asks for date-time, we treat the input date as the start of that day.
    const query = `SELECT id, timestamp FROM clicks WHERE timestamp ${direction} ?`;
    
    db.all(query, [date], (err, rows) => {
        if (err) {
            return res.status(400).json({ error: 'Database error' });
        }
        
        if (!rows || rows.length === 0) {
            return res.status(404).json({ error: 'No clicks found' });
        }

        res.status(200).json(rows);
    });
});

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}/`);
});