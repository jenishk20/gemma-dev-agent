const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();

app.use(express.json());

// Initialize Database
const db = new sqlite3.Database('db.sqlite3');

// Create table to store products. 
// Since the schema requires "unstructured properties", we store the 
// core 'name' as a primary key and the rest of the properties as a JSON string.
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        properties TEXT
    )`);
});

// POST /add: Add a new product
app.post('/add', (req, res) => {
    const body = req.body;
    if (!body || typeof body !== 'object' || !body.name) {
        return res.status(400).send('Invalid input: name is required');
    }

    const { name, ...properties } = body;
    
    // Ensure all additional properties are strings as per OpenAPI schema
    for (const key in properties) {
        if (typeof properties[key] !== 'string') {
            return res.status(400).send(`Property ${key} must be a string`);
        }
    }

    const propertiesJson = JSON.stringify(properties);

    const stmt = db.prepare("INSERT INTO products (name, properties) VALUES (?, ?)");
    stmt.run(name, propertiesJson, function(err) {
        if (err) {
            if (err.message.includes('UNIQUE constraint failed')) {
                return res.status(400).send('Product with this name already exists');
            }
            return res.status(500).send('Internal Server Error');
        }
        res.status(201).send('Product successfully added');
    });
    stmt.finalize();
});

// GET /download: Download product data
app.get('/download', (req, res) => {
    const name = req.query.name;
    if (!name) {
        return res.status(400).send('Query parameter "name" is required');
    }

    db.get("SELECT properties FROM products WHERE name = ?", [name], (err, row) => {
        if (err) return res.status(500).send('Internal Server Error');
        if (!row) return res.status(404).send('Product not found');

        // The schema says "data" should be a string. 
        // We return the properties object as a JSON string.
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

    // Validate that data is a valid JSON object of strings
    try {
        const parsed = JSON.parse(data);
        if (typeof parsed !== 'object' || parsed === null) throw new Error();
        for (const key in parsed) {
            if (typeof parsed[key] !== 'string') throw new Error();
        }
    } catch (e) {
        return res.status(400).send('Invalid data format: must be a JSON object of strings');
    }

    db.run("UPDATE products SET properties = ? WHERE name = ?", [data, name], function(err) {
        if (err) return res.status(500).send('Internal Server Error');
        if (this.changes === 0) return res.status(404).send('Product not found');
        res.status(200).send('The product with the given name was updated.');
    });
});

// GET /search: Search for products
app.get('/search', (req, res) => {
    const query = req.query.query;
    if (!query) {
        return res.status(400).send('Query parameter "query" is required');
    }

    // We search the name and the JSON properties string
    const sql = "SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?";
    const searchParam = `%${query}%`;

    db.all(sql, [searchParam, searchParam], (err, rows) => {
        if (err) return res.status(500).send('Internal Server Error');

        const results = rows.map(row => {
            const props = JSON.parse(row.properties || '{}');
            return {
                name: row.name,
                ...props
            };
        });

        res.json({ results });
    });
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});