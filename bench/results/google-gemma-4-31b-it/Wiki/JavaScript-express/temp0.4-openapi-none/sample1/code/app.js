const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const app = express();
const port = 5000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database Setup
const db = new sqlite3.Database('./db.sqlite3');

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS entries (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT,
        lastModifiedBy TEXT,
        lastModifiedAt TEXT
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entryId TEXT,
        content TEXT,
        modifiedBy TEXT,
        summary TEXT,
        modifiedAt TEXT,
        FOREIGN KEY(entryId) REFERENCES entries(id)
    )`);
});

// Helper to render simple HTML
const renderLayout = (title, content) => `
<!DOCTYPE html>
<html>
<head>
    <title>${title} - Wiki</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        a { color: #007bff; text-decoration: none; }
        .entry-link { display: block; margin: 10px 0; font-size: 1.2em; }
        .meta { font-size: 0.8em; color: #666; margin-bottom: 20px; }
        textarea { width: 100%; height: 300px; margin: 10px 0; }
        .diff { background: #eee; padding: 10px; border-left: 4px solid #ccc; margin: 10px 0; white-space: pre-wrap; }
        .btn { padding: 10px 15px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <nav><a href="/entries">🏠 Home</a> | <a href="/entries/new">➕ New Entry</a></nav>
        <hr>
        ${content}
    </div>
</body>
</html>`;

// Routes

// GET /entries - List all entries
app.get('/entries', (req, res) => {
    db.all("SELECT id, title FROM entries", [], (err, rows) => {
        if (err) return res.status(500).send(err.message);
        let listHtml = '<h1>Wiki Entries</h1>';
        if (rows.length === 0) {
            listHtml += '<p>No entries yet.</p>';
        } else {
            rows.forEach(row => {
                listHtml += `<a class="entry-link" href="/entries/${row.id}">${row.title}</a>`;
            });
        }
        res.send(renderLayout('Home', listHtml));
    });
});

// POST /entries - Create entry
app.post('/entries', (req, res) => {
    const { title, content, createdBy } = req.body;
    if (!title || !content || !createdBy) {
        return res.status(400).json({ error: "Missing required fields" });
    }
    const id = uuidv4();
    const now = new Date().toISOString();
    
    db.run("INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)", 
        [id, title, content, createdBy, now], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        
        db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)", 
            [id, content, createdBy, "Initial creation", now], (err) => {
            if (err) return res.status(500).json({ error: err.message });
            res.status(201).json({ id, title, content, lastModifiedBy: createdBy, lastModifiedAt: now });
        });
    });
});

// GET /entries/{id} - View entry
app.get('/entries/:entryId', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (err) return res.status(500).send(err.message);
        if (!row) return res.status(404).send("Entry not found");

        // Get contributors list
        db.all("SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?", [entryId], (err, contributors) => {
            const contributorList = contributors.map(c => c.modifiedBy).join(", ");
            const contentHtml = `
                <h1>${row.title}</h1>
                <div class="meta">
                    Last modified by ${row.lastModifiedBy} on ${row.lastModifiedAt}<br>
                    Contributors: ${contributorList}
                </div>
                <div style="white-space: pre-wrap;">${row.content}</div>
                <hr>
                <a href="/entries/${row.id}/edit">📝 Edit this page</a> | 
                <a href="/entries/${row.id}/edits">📜 History</a>
            `;
            res.send(renderLayout(row.title, contentHtml));
        });
    });
});

// UI Route for editing (not in OpenAPI but needed for the webapp)
app.get('/entries/new', (req, res) => {
    res.send(renderLayout('New Entry', `
        <h1>Create New Entry</h1>
        <form action="/entries" method="POST">
            <input type="text" name="title" placeholder="Title" required style="width:100%; margin-bottom:10px;"><br>
            <input type="text" name="createdBy" placeholder="Your Name" required style="width:100%; margin-bottom:10px;"><br>
            <textarea name="content" placeholder="Content..." required></textarea><br>
            <button type="submit" class="btn">Save Entry</button>
        </form>
    `));
});

app.get('/entries/:entryId/edit', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).send("Not found");
        res.send(renderLayout(`Editing ${row.title}`, `
            <h1>Edit: ${row.title}</h1>
            <form action="/entries/${row.id}" method="POST" style="display:flex; flex-direction:column;">
                <input type="hidden" name="_method" value="PUT">
                <input type="text" name="modifiedBy" placeholder="Your Name" required style="margin-bottom:10px;"><br>
                <input type="text" name="summary" placeholder="Edit summary (e.g. Fixed typo)" required style="margin-bottom:10px;"><br>
                <textarea name="content" required>${row.content}</textarea><br>
                <button type="submit" class="btn">Update Entry</button>
            </form>
        `));
    });
});

// Middleware to handle PUT requests from HTML forms
app.use((req, res, next) => {
    if (req.method === 'POST' && req.body._method === 'PUT') {
        req.method = 'PUT';
    }
    next();
});

// PUT /entries/{id} - Update entry
app.put('/entries/:entryId', (req, res) => {
    const { entryId } = req.params;
    const { content, modifiedBy, summary } = req.body;

    if (!content || !modifiedBy || !summary) {
        return res.status(400).json({ error: "Missing required fields" });
    }

    const now = new Date().toISOString();

    db.run("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
        [content, modifiedBy, now, entryId], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        if (this.changes === 0) return res.status(404).json({ error: "Entry not found" });

        db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)", 
            [entryId, content, modifiedBy, summary, now], (err) => {
            if (err) return res.status(500).json({ error: err.message });
            
            db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
                if (req.header('accept').includes('text/html')) {
                    res.redirect(`/entries/${entryId}`);
                } else {
                    res.json(row);
                }
            });
        });
    });
});

// GET /entries/{id}/edits - History
app.get('/entries/:entryId/edits', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT title FROM entries WHERE id = ?", [entryId], (err, entry) => {
        if (!entry) return res.status(404).send("Entry not found");

        db.all("SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", [entryId], (err, rows) => {
            let historyHtml = `<h1>History: ${entry.title}</h1>`;
            if (rows.length === 0) {
                historyHtml += '<p>No history available.</p>';
            } else {
                rows.forEach((edit, index) => {
                    historyHtml += `
                        <div style="border-bottom: 1px solid #ccc; padding: 10px 0;">
                            <strong>${edit.modifiedBy}</strong> (${edit.modifiedAt})<br>
                            <em>"${edit.summary}"</em>
                            <div class="diff">${edit.content}</div>
                        </div>
                    `;
                });
            }
            res.send(renderLayout(`History - ${entry.title}`, historyHtml));
        });
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Wiki app listening at http://0.0.0.0:${port}`);
});