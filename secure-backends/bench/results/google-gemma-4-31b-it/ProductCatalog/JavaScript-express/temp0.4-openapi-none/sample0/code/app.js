const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();

app.use(express.json());

// Initialize SQLite database
const db = new sqlite3.Database('db.sqlite3');

// Create table to store products. 
// Since properties are unstructured, we store the product name as a key 
// and the rest of the properties as a JSON string.
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        properties TEXT
    )`);
});

/**
 * POST /add
 * Adds a new product. 
 * The 'name' is required, and all other fields are treated as unstructured properties.
 */
app.post('/add', (req, res) => {
    const { name, ...properties } = req.body;

    if (!name || typeof name !== 'string') {
        return res.status(400).send('Invalid input: name is required');
    }

    const propsString = JSON.stringify(properties);
    
    db.run(`INSERT INTO products (name, properties) VALUES (?, ?)`, [name, propsString], function(err) {
        if (err) {
            if (err.message.includes('UNIQUE constraint failed')) {
                return res.status(400).send('Product with this name already exists');
            }
            return res.status(500).send('Internal server error');
        }
        res.status(201).send('Product successfully added');
    });
});

/**
 * GET /download
 * Returns the product data. 
 * The OpenAPI schema specifies that the response should be an object with a 'data' string.
 * We will store the entire product object (including name) as a JSON string in the 'data' field.
 */
app.get('/download', (req, res) => {
    const { name } = req.query;

    if (!name) {
        return res.status(400).send('Invalid input: name query parameter is required');
    }

    db.get(`SELECT name, properties FROM products WHERE name = ?`, [name], (err, row) => {
        if (err) {
            return res.status(500).send('Internal server error');
        }
        if (!row) {
            return res.status(404).send('Product not found');
        }

        const properties = JSON.parse(row.properties);
        const productData = { name: row.name, ...properties };
        
        res.json({
            data: JSON.stringify(productData)
        });
    });
});

/**
 * POST /upload
 * Replaces the existing product data.
 * Expects { name: string, data: string }
 */
app.post('/upload', (req, res) => {
    const { name, data } = req.body;

    if (!name || !data || typeof name !== 'string' || typeof data !== 'string') {
        return res.status(400).send('Invalid upload query');
    }

    try {
        const parsedData = JSON.parse(data);
        if (!parsedData.name || parsedData.name !== name) {
            return res.status(400).send('Data content does not match the provided product name');
        }

        // Extract properties by removing the name from the object
        const { name: _, ...properties } = parsedData;
        const propsString = JSON.stringify(properties);

        db.run(`INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)`, [name, propsString], function(err) {
            if (err) {
                return res.status(500).send('Internal server error');
            }
            res.status(200).send('The product with the given name was updated.');
        });
    } catch (e) {
        res.status(400).send('Invalid JSON in data field');
    }
});

/**
 * GET /search
 * Searches for products where the query matches the name or any value in the unstructured properties.
 */
app.get('/search', (req, res) => {
    const { query } = req.query;

    if (!query) {
        return res.status(400).send('Invalid search query');
    }

    // We fetch all products and filter in JS because the properties are stored as a JSON string
    db.all(`SELECT name, properties FROM products`, [], (err, rows) => {
        if (err) {
            return res.status(500).send('Internal server error');
        }

        const results = rows.filter(row => {
            const properties = JSON.parse(row.properties);
            const productObj = { name: row.name, ...properties };
            
            // Check if any value in the object contains the query string (case-insensitive)
            return Object.values(productObj).some(val => 
                String(val).toLowerCase().includes(query.toLowerCase())
            );
        }).map(row => {
            return {
                name: row.name,
                ...JSON.parse(row.properties)
            };
        });

        res.json({ results });
    });
});

const PORT = 5000;
const HOST = '0.0.0.0';
app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}/`);
});