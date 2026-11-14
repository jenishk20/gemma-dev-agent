const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const LOG_FILE = path.join(__dirname, 'logs.txt');

// Middleware to parse JSON bodies
app.use(express.json());

/**
 * POST /log
 * Logs a message to the server.
 * Expects JSON: { "message": "string" }
 */
app.post('/log', (req, res) => {
    const { message } = req.body;

    if (typeof message !== 'string') {
        return res.status(400).send('Invalid request: "message" property is required and must be a string.');
    }

    // Append the message to logs.txt with a newline
    fs.appendFile(LOG_FILE, message + '\n', (err) => {
        if (err) {
            console.error('Error writing to log file:', err);
            return res.status(500).send('Internal Server Error');
        }
        res.status(200).send('Log message successful');
    });
});

/**
 * GET /logs
 * Retrieve all logged messages.
 * Returns content as text/plain.
 */
app.get('/logs', (req, res) => {
    fs.readFile(LOG_FILE, 'utf8', (err, data) => {
        if (err) {
            // If file doesn't exist yet, return empty string instead of 500
            if (err.code === 'ENOENT') {
                return res.status(200).set('Content-Type', 'text/plain').send('');
            }
            console.error('Error reading log file:', err);
            return res.status(500).send('Internal Server Error');
        }
        res.status(200).set('Content-Type', 'text/plain').send(data);
    });
});

app.listen(PORT, HOST, () => {
    console.log(`LoggingAPI running at http://${HOST}:${PORT}`);
});