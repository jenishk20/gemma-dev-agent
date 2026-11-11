const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const LOG_FILE = path.join(__dirname, 'logs.txt');

app.use(express.json());

// POST /log - Log a message
app.post('/log', (req, res) => {
    const { message } = req.body;

    if (typeof message !== 'string') {
        return res.status(400).send('Invalid request: message must be a string');
    }

    // Append message to logs.txt, each message on a new line
    fs.appendFile(LOG_FILE, message + '\n', (err) => {
        if (err) {
            console.error('Error writing to log file:', err);
            return res.status(500).send('Internal Server Error');
        }
        res.status(200).send('Log message successful');
    });
});

// GET /logs - Retrieve all logs
app.get('/logs', (req, res) => {
    fs.readFile(LOG_FILE, 'utf8', (err, data) => {
        if (err) {
            // If file doesn't exist yet, return empty string
            if (err.code === 'ENOENT') {
                return res.status(200).send('');
            }
            console.error('Error reading log file:', err);
            return res.status(500).send('Internal Server Error');
        }
        res.status(200).setHeader('Content-Type', 'text/plain').send(data);
    });
});

app.listen(PORT, HOST, () => {
    console.log(`LoggingAPI running at http://${HOST}:${PORT}`);
});