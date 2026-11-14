const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const app = express();
const port = 5000;
const db = new sqlite3.Database('db.sqlite3');

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize Database
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

// Helper to render simple HTML templates
const renderHTML = (content) => `
<!DOCTYPE html>
<html>
<head>
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-card { border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px; }
        .diff-box { background: #f4f4f4; padding: 10px; border-left: 4px solid #ccc; margin: 10px 0; white-space: pre-wrap; }
        textarea { width: 100%; height: 200px; }
        input { display: block; margin: 10px 0; width: 100%; padding: 5px; }
        button { cursor: pointer; padding: 10px 20px; }
    </style>
</head>
<body>
    <nav><a href="/entries">🏠 Home</a> | <a href="/entries/new">➕ New Entry</a></nav>
    ${content}
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
                listHtml += `<div class="entry-card"><strong><a href="/entries/${row.id}">${row.title}</a></strong></div>`;
            });
        }
        res.send(renderHTML(listHtml));
    });
});

// Page to create new entry (Frontend for POST /entries)
app.get('/entries/new', (req, res) => {
    const form = `
        <h1>Create New Entry</h1>
        <form action="/entries" method="POST">
            <input type="text" name="title" placeholder="Title" required><br>
            <input type="text" name="createdBy" placeholder="Your Name" required><br>
            <textarea name="content" placeholder="Content" required></textarea><br>
            <button type="submit">Create Entry</button>
        </form>
    `;
    res.send(renderHTML(form));
});

// POST /entries - Create entry
app.post('/entries', (req, res) => {
    // Handle both JSON and Form-urlencoded
    const { title, content, createdBy } = req.body;
    if (!title || !content || !createdBy) {
        return res.status(400).json({ error: "Missing required fields" });
    }

    const id = uuidv4();
    const now = new Date().toISOString();

    db.serialize(() => {
        db.run("INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)", 
            [id, title, content, createdBy, now]);
        db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)", 
            [id, content, createdBy, "Initial creation", now]);
    });

    res.status(201).json({ id, title, content, lastModifiedBy: createdBy, lastModifiedAt: now });
});

// GET /entries/{entryId} - View entry
app.get('/entries/:entryId', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (err) return res.status(500).send(err.message);
        if (!row) return res.status(404).send("Entry not found");

        const content = `
            <h1>${row.title}</h1>
            <p style="font-size: 0.8em; color: #666;">Last modified by ${row.lastModifiedBy} on ${row.lastModifiedAt}</p>
            <div style="border: 1px solid #eee; padding: 15px; background: #fafafa;">${row.content}</div>
            <hr>
            <a href="/entries/${row.id}/edit">📝 Edit this page</a> | 
            <a href="/entries/${row.id}/edits">📜 View History</a>
        `;
        res.send(renderHTML(content));
    });
});

// Page to edit entry (Frontend for PUT /entries/{entryId})
app.get('/entries/:entryId/edit', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).send("Entry not found");
        const form = `
            <h1>Edit: ${row.title}</h1>
            <form action="/entries/${row.id}/update" method="POST">
                <input type="hidden" name="_method" value="PUT">
                <input type="text" name="modifiedBy" placeholder="Your Name" required><br>
                <input type="text" name="summary" placeholder="Edit Summary (e.g. Fixed typo)" required><br>
                <textarea name="content" required>${row.content}</textarea><br>
                <button type="submit">Save Changes</button>
            </form>
        `;
        res.send(renderHTML(form));
    });
});

// Middleware to handle PUT via POST (since HTML forms only support GET/POST)
app.use((req, res, next) => {
    if (req.method === 'POST' && req.body._method === 'PUT') {
        req.method = 'PUT';
    }
    next();
});

// PUT /entries/{entryId} - Update entry
app.put('/entries/:entryId/update', (req, res) => {
    const { entryId } = req.params;
    const { content, modifiedBy, summary } = req.body;

    if (!content || !modifiedBy || !summary) {
        return res.status(400).json({ error: "Missing required fields" });
    }

    const now = new Date().toISOString();

    db.get("SELECT id FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).json({ error: "Entry not found" });

        db.serialize(() => {
            db.run("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
                [content, modifiedBy, now, entryId]);
            db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)", 
                [entryId, content, modifiedBy, summary, now]);
        });

        res.json({ id: entryId, content, lastModifiedBy: modifiedBy, lastModifiedAt: now });
    });
});

// GET /entries/{entryId}/edits - Edit history
app.get('/entries/:entryId/edits', (req, res) => {
    const { entryId } = req.params;
    db.all("SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", [entryId], (err, rows) => {
        if (err) return res.status(500).send(err.message);
        if (rows.length === 0) return res.status(404).send("Entry not found or no edits");

        let historyHtml = `<h1>Edit History</h1>`;
        rows.forEach((edit, index) => {
            historyHtml += `
                <div class="entry-card">
                    <strong>${edit.modifiedBy}</strong> - ${edit.modifiedAt}<br>
                    <em>Summary: ${edit.summary}</em>
                    <div class="diff-box">${edit.content}</div>
                </div>
            `;
        });
        historyHtml += `<p><a href="/entries/${entryId}">← Back to entry</a></p>`;
        res.send(renderHTML(historyHtml));
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Wiki server running at http://0.0.0.0:${port}`);
});