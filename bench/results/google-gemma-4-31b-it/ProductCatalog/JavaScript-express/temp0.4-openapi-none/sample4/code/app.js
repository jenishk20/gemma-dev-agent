const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();

app.use(express.json());

// Initialize Database
const db = new sqlite3.Database('db.sqlite3');

// We use a table with a 'name' (primary key) and a 'properties' column 
// storing a JSON string to handle the "unstructured properties" requirement.
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        properties TEXT
    )`);
});

/**
 * POST /add
 * Adds a new product. 
 * The 'name' is the key, and all other fields are stored as a JSON string.
 */
app.post('/add', (req, res) => {
    const body = req.body;
    if (!body || typeof body !== 'object' || !body.name) {
        return res.status(400).send('Invalid input: name is required');
    }

    const { name, ...properties } = body;
    
    // Validate that all additional properties are strings as per schema
    for (const key in properties) {
        if (typeof properties[key] !== 'string') {
            return res.status(400).send(`Property ${key} must be a string`);
        }
    }

    const propsJson = JSON.stringify(properties);

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

/**
 * GET /download
 * Returns the product data. 
 * The schema specifies the response as an object with a 'data' string.
 */
app.get('/download', (req, res) => {
    const name = req.query.name;
    if (!name) {
        return res.status(400).send('Query parameter "name" is required');
    }

    db.get('SELECT name, properties FROM products WHERE name = ?', [name], (err, row) => {
        if (err) return res.status(500).send('Internal Server Error');
        if (!row) return res.status(404).send('Product not found');

        // Reconstruct the full object (name + properties) and stringify it for the 'data' field
        const fullProduct = { name: row.name, ...JSON.parse(row.properties) };
        res.json({ data: JSON.stringify(fullProduct) });
    });
});

/**
 * POST /upload
 * Replaces existing product data.
 * Expects { name: "...", data: "stringified_json" }
 */
app.post('/upload', (req, res) => {
    const { name, data } = req.body;
    if (!name || !data) {
        return res.status(400).send('Invalid upload query: name and data are required');
    }

    try {
        const parsedData = JSON.parse(data);
        if (!parsedData || typeof parsedData !== 'object' || parsedData.name !== name) {
            throw new Error('Data content does not match product name');
        }
        
        const { name: _, ...properties } = parsedData;
        const propsJson = JSON.stringify(properties);

        db.run('REPLACE INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function(err) {
            if (err) return res.status(500).send('Internal Server Error');
            res.status(200).send('The product with the given name was updated.');
        });
    } catch (e) {
        res.status(400).send('Invalid upload query: data must be a valid JSON string');
    }
});

/**
 * GET /search
 * Searches for a query string in the name or any of the unstructured properties.
 */
app.get('/search', (req, res) => {
    const query = req.query.query;
    if (!query) {
        return res.status(400).send('Query parameter "query" is required');
    }

    // We fetch all and filter in JS because SQLite JSON searching varies by version.
    // For a production app, we'd use json_each or a full-text search index.
    db.all('SELECT name, properties FROM products', [], (err, rows) => {
        if (err) return res.status(500).send('Internal Server Error');

        const results = rows.filter(row => {
            const props = JSON.parse(row.properties);
            const nameMatch = row.name.toLowerCase().includes(query.toLowerCase());
            const propMatch = Object.values(props).some(val => 
                val.toLowerCase().includes(query.toLowerCase())
            );
            return nameMatch || propMatch;
        }).map(row => ({
            name: row.name,
            ...JSON.parse(row.properties)
        }));

        res.json({ results });
    });
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});