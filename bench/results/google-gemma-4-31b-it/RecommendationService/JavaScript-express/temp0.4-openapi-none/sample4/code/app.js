const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = 5000;
const host = '0.0.0.0';

app.use(express.json());

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    // Products table
    db.run(`CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL
    )`);

    // Tags table
    db.run(`CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        tag_name TEXT NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )`);
});

// GET /recommender
app.get('/recommender', (req, res) => {
    const tagsQuery = req.query.tags;

    if (!tagsQuery) {
        return res.status(400).send('Missing tags query parameter');
    }

    const searchTags = tagsQuery.split(',').map(t => t.trim()).filter(t => t !== '');
    
    if (searchTags.length === 0) {
        return res.send('<h1>No products found</h1>');
    }

    // Build a query to find products that have at least one of the tags
    // Using a parameterized query to prevent SQL injection
    const placeholders = searchTags.map(() => '?').join(',');
    const sql = `
        SELECT DISTINCT p.product_name 
        FROM products p 
        JOIN tags t ON p.id = t.product_id 
        WHERE t.tag_name IN (${placeholders})
    `;

    db.all(sql, searchTags, (err, rows) => {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }

        if (rows.length === 0) {
            return res.send('<h1>No products match the provided tags.</h1>');
        }

        let htmlResponse = '<h1>Recommended Products</h1><ul>';
        rows.forEach(row => {
            htmlResponse += `<li><a href="#">${row.product_name}</a></li>`;
        });
        htmlResponse += '</ul>';
        
        res.setHeader('Content-Type', 'text/html');
        res.status(200).send(htmlResponse);
    });
});

// POST /recommender
app.post('/recommender', (req, res) => {
    const { product_name, tags } = req.body;

    if (!product_name || !Array.isArray(tags)) {
        return res.status(400).send('Invalid input: product_name and tags (array) are required');
    }

    db.serialize(() => {
        db.run('BEGIN TRANSACTION');

        const productStmt = db.prepare('INSERT INTO products (product_name) VALUES (?)');
        productStmt.run(product_name, function(err) {
            if (err) {
                db.run('ROLLBACK');
                return res.status(500).send('Database error');
            }

            const productId = this.lastID;
            const tagStmt = db.prepare('INSERT INTO tags (product_id, tag_name) VALUES (?, ?)');

            let errorOccurred = false;
            tags.forEach(tag => {
                tagStmt.run(productId, tag, (err) => {
                    if (err) errorOccurred = true;
                });
            });

            tagStmt.finalize();

            if (errorOccurred) {
                db.run('ROLLBACK');
                return res.status(500).send('Database error inserting tags');
            }

            db.run('COMMIT', (err) => {
                if (err) {
                    return res.status(500).send('Commit error');
                }
                res.status(200).send('Successful operation');
            });
        });
        productStmt.finalize();
    });
});

app.listen(port, host, () => {
    console.log(`Server running at http://${host}:${port}/`);
});