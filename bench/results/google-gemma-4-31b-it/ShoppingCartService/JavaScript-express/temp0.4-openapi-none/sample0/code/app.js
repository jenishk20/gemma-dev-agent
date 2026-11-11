const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = express();
app.use(express.json());

const db = new sqlite3.Database('db.sqlite3');

// Initialize database schema
db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS carts (
      cart_id TEXT PRIMARY KEY
    )
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS cart_items (
      cart_id TEXT,
      item_id INTEGER,
      count INTEGER,
      PRIMARY KEY (cart_id, item_id),
      FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
    )
  `);
});

// POST /create_cart
app.post('/create_cart', (req, res) => {
  const cart_id = uuidv4();
  db.run('INSERT INTO carts (cart_id) VALUES (?)', [cart_id], function(err) {
    if (err) {
      return res.status(500).json({ error: 'Internal server error' });
    }
    res.status(201).json({ cart_id });
  });
});

// POST /add_to_cart
app.post('/add_to_cart', (req, res) => {
  const { cart_id, item_id, count } = req.body;

  if (cart_id === undefined || item_id === undefined || count === undefined) {
    return res.status(400).json({ error: 'Missing required fields: cart_id, item_id, count' });
  }

  // Check if cart exists
  db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
    if (err) return res.status(500).json({ error: 'Database error' });
    if (!row) return res.status(404).json({ error: 'Cart not found' });

    // Update or insert item count
    db.run(
      `INSERT INTO cart_items (cart_id, item_id, count) 
       VALUES (?, ?, ?) 
       ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count`,
      [cart_id, item_id, count],
      function(err) {
        if (err) return res.status(500).json({ error: 'Database error' });

        // Clean up items with 0 or negative count
        db.run('DELETE FROM cart_items WHERE count <= 0', (err) => {
          if (err) console.error('Cleanup error:', err);
          res.status(200).send();
        });
      }
    );
  });
});

// POST /retrieve_cart
app.post('/retrieve_cart', (req, res) => {
  const { cart_id } = req.body;

  if (!cart_id) {
    return res.status(400).json({ error: 'Missing required field: cart_id' });
  }

  // Check if cart exists
  db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
    if (err) return res.status(500).json({ error: 'Database error' });
    if (!row) return res.status(404).json({ error: 'Cart not found' });

    db.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id], (err, rows) => {
      if (err) return res.status(500).json({ error: 'Database error' });
      
      const items = rows.map(row => ({
        item_id: row.item_id,
        count: row.count
      }));
      
      res.status(200).json({ items });
    });
  });
});

app.listen(5000, '0.0.0.0', () => {
  console.log('Shopping Cart Service running on port 5000');
});