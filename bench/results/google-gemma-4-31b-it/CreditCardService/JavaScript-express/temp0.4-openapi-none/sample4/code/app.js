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
        card_number TEXT,
        phone_number TEXT,
        PRIMARY KEY (card_number, phone_number)
    )`);
});

/**
 * POST /associate_card
 * Create a new association of a credit card number with a phone number.
 */
app.post('/associate_card', (req, res) => {
    const { credit_card, phone } = req.body;

    if (!credit_card || !phone) {
        return res.status(400).send('Invalid request: credit_card and phone are required');
    }

    const stmt = db.prepare('INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)');
    stmt.run(credit_card, phone, function(err) {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }
        res.status(201).send('Association created successfully');
    });
    stmt.finalize();
});

/**
 * POST /retrieve_cards
 * Retrieve cards associated with all given phone numbers.
 */
app.post('/retrieve_cards', (req, res) => {
    const { phone_numbers } = req.body;

    if (!phone_numbers || !Array.isArray(phone_numbers)) {
        return res.status(400).send('Invalid request: phone_numbers array is required');
    }

    if (phone_numbers.length === 0) {
        return res.status(200).json({ card_numbers: [] });
    }

    // To find cards associated with ALL provided phone numbers:
    // We group by card_number and filter for those where the count of distinct 
    // phone numbers matching the input list equals the length of the input list.
    const placeholders = phone_numbers.map(() => '?').join(',');
    const query = `
        SELECT card_number 
        FROM associations 
        WHERE phone_number IN (${placeholders}) 
        GROUP BY card_number 
        HAVING COUNT(DISTINCT phone_number) = ?
    `;

    const params = [...phone_numbers, phone_numbers.length];

    db.all(query, params, (err, rows) => {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }

        const card_numbers = rows.map(row => row.card_number);
        
        if (card_numbers.length === 0) {
            // The schema suggests 404 for Not Found, though 200 with empty list is also common.
            // Following the schema's 404 response definition.
            return res.status(404).send('Not found');
        }

        res.status(200).json({ card_numbers });
    });
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}/`);
});