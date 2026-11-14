const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = 5000;
const host = '0.0.0.0';

app.use(express.json());

// Database initialization
const db = new sqlite3.Database('./db.sqlite3', (err) => {
    if (err) {
        console.error('Error opening database', err);
    }
});

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL
    )`);
    db.run(`CREATE TABLE IF NOT EXISTS tags (
        product_id INTEGER,
        tag TEXT NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )`);
});

// GET /recommender
app.get('/recommender', (req, res) => {
    const tagsQuery = req.query.tags;

    if (!tagsQuery) {
        return res.status(400).send('Query parameter "tags" is required');
    }

    const tagsList = tagsQuery.split(',').map(t => t.trim()).filter(t => t !== '');
    
    if (tagsList.length === 0) {
        return res.status(400).send('No valid tags provided');
    }

    // Build a query to find products that have at least one of the tags
    // Using placeholders to prevent SQL injection
    const placeholders = tagsList.map(() => '?').join(',');
    const sql = `
        SELECT DISTINCT p.product_name 
        FROM products p 
        JOIN tags t ON p.id = t.product_id 
        WHERE t.tag IN (${placeholders})
    `;

    db.all(sql, tagsList, (err, rows) => {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }

        if (rows.length === 0) {
            return res.send('<h1>No products found matching those tags.</h1>');
        }

        let htmlResponse = '<h1>Recommended Products</h1><ul>';
        rows.forEach(row => {
            htmlResponse += `<li>${row.product_name}</li>`;
        });
        htmlResponse += '</ul>';
        
        res.setHeader('Content-Type', 'text/html');
        res.status(200).send(htmlResponse);
    });
});

// POST /recommender
app.post('/recommender', (req, res) => {
    const { product_name, tags } = req.body;

    if (!product_name || !Array.isArray(tags) || tags.length === 0) {
        return res.status(400).send('Invalid input: product_name and a non-empty tags array are required');
    }

    db.serialize(() => {
        db.run('BEGIN TRANSACTION');
        
        const stmt = db.prepare('INSERT INTO products (product_name) VALUES (?)');
        stmt.run(product_name, function(err) {
            if (err) {
                db.run('ROLLBACK');
                return res.status(500).send('Error inserting product');
            }

            const productId = this.lastID;
            const tagStmt = db.prepare('INSERT INTO tags (product_id, tag) VALUES (?, ?)');
            
            let errorOccurred = false;
            tags.forEach(tag => {
                tagStmt.run(productId, tag, (err) => {
                    if (err) errorOccurred = true;
                });
            });

            tagStmt.finalize();

            if (errorOccurred) {
                db.run('ROLLBACK');
                return res.status(500).send('Error inserting tags');
            } else {
                db.run('COMMIT', (err) => {
                    if (err) return res.status(500).send('Commit failed');
                    res.status(200).send('Successful operation');
                });
            }
        });
        stmt.finalize();
    });
});

app.listen(port, host, () => {
    console.log(`Server running at http://${host}:${port}/`);
});