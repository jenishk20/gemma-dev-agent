const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();

app.use(express.json());

// Initialize SQLite Database
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
 * The 'name' is the primary key, other fields are stored in the properties JSON.
 */
app.post('/add', (req, res) => {
    const body = req.body;
    if (!body || typeof body !== 'object' || !body.name) {
        return res.status(400).send('Invalid input: name is required');
    }

    const { name, ...properties } = body;
    
    // Validate that all additional properties are strings as per OpenAPI schema
    for (const key in properties) {
        if (typeof properties[key] !== 'string') {
            return res.status(400).send('All additional properties must be strings');
        }
    }

    const propsJson = JSON.stringify(properties);
    const stmt = db.prepare("INSERT INTO products (name, properties) VALUES (?, ?)");
    
    stmt.run(name, propsJson, function(err) {
        if (err) {
            return res.status(400).send('Product already exists or database error');
        }
        res.status(201).send('Product successfully added');
    });
    stmt.finalize();
});

/**
 * GET /download
 * Returns the product data as a JSON string in the 'data' field.
 */
app.get('/download', (req, res) => {
    const name = req.query.name;
    if (!name) {
        return res.status(400).send('Query parameter "name" is required');
    }

    db.get("SELECT name, properties FROM products WHERE name = ?", [name], (err, row) => {
        if (err || !row) {
            return res.status(400).send('Product not found');
        }
        
        // The schema asks for the "data" of the product. 
        // We reconstruct the object (name + properties) and stringify it.
        const productObj = { name: row.name, ...JSON.parse(row.properties) };
        res.json({ data: JSON.stringify(productObj) });
    });
});

/**
 * POST /upload
 * Replaces product data. Expects { name, data } where data is the JSON string from /download.
 */
app.post('/upload', (req, res) => {
    const { name, data } = req.body;
    if (!name || !data) {
        return res.status(400).send('Invalid upload query: name and data are required');
    }

    try {
        const parsedData = JSON.parse(data);
        if (!parsedData.name || parsedData.name !== name) {
            throw new Error('Data name mismatch');
        }

        const { name: _, ...properties } = parsedData;
        const propsJson = JSON.stringify(properties);

        db.run("UPDATE products SET properties = ? WHERE name = ?", [propsJson, name], function(err) {
            if (err) return res.status(400).send('Database error');
            if (this.changes === 0) return res.status(400).send('Product not found');
            res.status(200).send('The product with the given name was updated.');
        });
    } catch (e) {
        res.status(400).send('Invalid data format');
    }
});

/**
 * GET /search
 * Searches for products where the name or any property value contains the query string.
 */
app.get('/search', (req, res) => {
    const query = req.query.query;
    if (!query) {
        return res.status(400).send('Query parameter "query" is required');
    }

    db.all("SELECT name, properties FROM products", [], (err, rows) => {
        if (err) return res.status(500).send('Database error');

        const results = rows.filter(row => {
            const props = JSON.parse(row.properties);
            // Check name
            if (row.name.toLowerCase().includes(query.toLowerCase())) return true;
            // Check all unstructured properties
            for (const key in props) {
                if (props[key].toLowerCase().includes(query.toLowerCase())) return true;
            }
            return false;
        }).map(row => {
            return { name: row.name, ...JSON.parse(row.properties) };
        });

        res.json({ results });
    });
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});