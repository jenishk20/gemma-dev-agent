const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = 5000;

// Middleware
app.use(express.json());

// Database Setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    // Table for products
    db.run(`CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL
    )`);

    // Table for tags
    db.run(`CREATE TABLE IF NOT EXISTS tags (
        product_id INTEGER,
        tag TEXT NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )`);
});

/**
 * GET /recommender
 * Returns a list of products that match at least one of the provided tags.
 * Response is in HTML format.
 */
app.get('/recommender', (req, res) => {
    const tagsQuery = req.query.tags;

    if (!tagsQuery) {
        return res.status(400).send('Missing required query parameter: tags');
    }

    const searchTags = tagsQuery.split(',').map(t => t.trim()).filter(t => t.length > 0);

    if (searchTags.length === 0) {
        return res.send('<h1>No tags provided</h1>');
    }

    // Use placeholders to prevent SQL injection
    const placeholders = searchTags.map(() => '?').join(',');
    const sql = `
        SELECT DISTINCT p.product_name 
        FROM products p 
        JOIN tags t ON p.id = t.product_id 
        WHERE t.tag IN (${placeholders})
    `;

    db.all(sql, searchTags, (err, rows) => {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }

        if (rows.length === 0) {
            return res.send('<h1>No products found matching those tags.</h1>');
        }

        let html = '<h1>Recommended Products</h1><ul>';
        rows.forEach(row => {
            html += `<li><a href="#">${row.product_name}</a></li>`;
        });
        html += '</ul>';
        
        res.setHeader('Content-Type', 'text/html');
        res.status(200).send(html);
    });
});

/**
 * POST /recommender
 * Posts a new product along with its tags.
 */
app.post('/recommender', (req, res) => {
    const { product_name, tags } = req.body;

    if (!product_name || !Array.isArray(tags)) {
        return res.status(400).send('Invalid input: product_name (string) and tags (array) are required.');
    }

    db.serialize(() => {
        db.run('BEGIN TRANSACTION');

        const stmtProduct = db.prepare('INSERT INTO products (product_name) VALUES (?)');
        stmtProduct.run(product_name, function(err) {
            if (err) {
                db.run('ROLLBACK');
                return res.status(500).send('Error inserting product');
            }

            const productId = this.lastID;
            const stmtTag = db.prepare('INSERT INTO tags (product_id, tag) VALUES (?, ?)');

            let errorOccurred = false;
            tags.forEach(tag => {
                stmtTag.run(productId, tag, (err) => {
                    if (err) errorOccurred = true;
                });
            });

            stmtTag.finalize();

            if (errorOccurred) {
                db.run('ROLLBACK');
                return res.status(500).send('Error inserting tags');
            }

            db.run('COMMIT', (err) => {
                if (err) return res.status(500).send('Transaction commit failed');
                res.status(200).send('Successful operation');
            });
        });
        stmtProduct.finalize();
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${port}`);
});