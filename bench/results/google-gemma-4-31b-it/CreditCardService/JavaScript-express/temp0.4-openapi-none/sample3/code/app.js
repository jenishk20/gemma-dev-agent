const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const dotenv = require('dotenv');

dotenv.config();

const app = express();
app.use(express.json());

const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS associations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credit_card TEXT NOT NULL,
        phone TEXT NOT NULL
    )`);
    db.run(`CREATE INDEX IF NOT EXISTS idx_phone ON associations(phone)`);
    db.run(`CREATE INDEX IF NOT EXISTS idx_card ON associations(credit_card)`);
});

/**
 * POST /associate_card
 * Creates a new association between a credit card and a phone number.
 */
app.post('/associate_card', (req, res) => {
    const { credit_card, phone } = req.body;

    if (!credit_card || !phone) {
        return res.status(400).send('Invalid request: credit_card and phone are required');
    }

    const query = `INSERT INTO associations (credit_card, phone) VALUES (?, ?)`;
    db.run(query, [credit_card, phone], function(err) {
        if (err) {
            console.error(err);
            return res.status(500).send('Internal Server Error');
        }
        res.status(201).send('Association created successfully');
    });
});

/**
 * POST /retrieve_cards
 * Retrieve cards associated with ALL given phone numbers.
 */
app.post('/retrieve_cards', (req, res) => {
    const { phone_numbers } = req.body;

    if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
        return res.status(400).send('Invalid request: phone_numbers array is required');
    }

    // To find cards associated with ALL given phone numbers, we group by credit_card
    // and filter for those where the count of distinct phone numbers matches the input list length.
    const placeholders = phone_numbers.map(() => '?').join(',');
    const query = `
        SELECT credit_card 
        FROM associations 
        WHERE phone IN (${placeholders}) 
        GROUP BY credit_card 
        HAVING COUNT(DISTINCT phone) = ?
    `;

    const params = [...phone_numbers, phone_numbers.length];

    db.all(query, params, (err, rows) => {
        if (err) {
            console.error(err);
            return res.status(500).send('Internal Server Error');
        }

        if (!rows || rows.length === 0) {
            return res.status(404).json({ card_numbers: [] });
        }

        const cardNumbers = rows.map(row => row.credit_card);
        res.status(200).json({ card_numbers });
    });
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}/`);
});