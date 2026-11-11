const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();

app.use(express.json());

// Initialize Database
const db = new sqlite3.Database('db.sqlite3');

// Create table to store products. 
// Since properties are unstructured, we store the 'name' as a primary key 
// and the rest of the properties as a JSON string.
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        properties TEXT
    )`);
});

// Helper to extract properties from the JSON string stored in DB
const parseProperties = (name, jsonStr) => {
    const props = JSON.parse(jsonStr);
    return { name, ...props };
};

// POST /add: Add a new product
app.post('/add', (req, res) => {
    const body = req.body;
    if (!body || typeof body !== 'object' || !body.name) {
        return res.status(400).send('Invalid input: name is required');
    }

    const { name, ...additionalProperties } = body;
    
    // Validate that all additional properties are strings as per OpenAPI spec
    for (const key in additionalProperties) {
        if (typeof additionalProperties[key] !== 'string') {
            return res.status(400).send(`Property ${key} must be a string`);
        }
    }

    const propsJson = JSON.stringify(additionalProperties);

    db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function(err) {
        if (err) {
            if (err.message.includes('UNIQUE constraint failed')) {
                return res.status(400).send('Product with this name already exists');
            }
            return res.status(500).send('Internal Server Error');
        }
        res.status(201).send('Product successfully added');
    });
});

// GET /download: Download product data
app.get('/download', (req, res) => {
    const name = req.query.name;
    if (!name) {
        return res.status(400).send('Query parameter "name" is required');
    }

    db.get('SELECT properties FROM products WHERE name = ?', [name], (err, row) => {
        if (err) return res.status(500).send('Internal Server Error');
        if (!row) return res.status(404).send('Product not found');

        // The spec says return an object with a 'data' property containing the product data
        // The "data" is the string representation of the unstructured properties
        res.json({
            data: row.properties
        });
    });
});

// POST /upload: Update product data
app.post('/upload', (req, res) => {
    const { name, data } = req.body;
    if (!name || typeof data !== 'string') {
        return res.status(400).send('Invalid upload query: name and data (string) are required');
    }

    // Validate that the data string is valid JSON and contains only strings
    try {
        const parsed = JSON.parse(data);
        for (const key in parsed) {
            if (typeof parsed[key] !== 'string') throw new Error();
        }
    } catch (e) {
        return res.status(400).send('Invalid data format: must be a JSON string of string-fields');
    }

    db.run('UPDATE products SET properties = ? WHERE name = ?', [data, name], function(err) {
        if (err) return res.status(500).send('Internal Server Error');
        if (this.changes === 0) return res.status(404).send('Product not found');
        res.status(200).send('The product with the given name was updated.');
    });
});

// GET /search: Search products
app.get('/search', (req, res) => {
    const query = req.query.query;
    if (!query) {
        return res.status(400).send('Query parameter "query" is required');
    }

    // We search in the name column and the properties JSON column
    const sql = 'SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?';
    const searchParam = `%${query}%`;

    db.all(sql, [searchParam, searchParam], (err, rows) => {
        if (err) return res.status(500).send('Internal Server Error');

        const results = rows.map(row => {
            return parseProperties(row.name, row.properties);
        });

        res.json({ results });
    });
});

const PORT = 5000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
});