const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const app = express();
const db = new sqlite3.Database('db.sqlite3');

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database Initialization
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
const renderLayout = (title, body) => `
<!DOCTYPE html>
<html>
<head>
    <title>${title} - Wiki</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-card { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
        .diff-box { background: #f4f4f4; padding: 10px; border-left: 4px solid #ccc; margin: 10px 0; white-space: pre-wrap; }
        form { display: flex; flex-direction: column; gap: 10px; max-width: 500px; }
        input, textarea { padding: 8px; font-size: 1rem; }
        textarea { height: 200px; }
        button { cursor: pointer; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; }
    </style>
</head>
<body>
    <nav><a href="/entries">🏠 Home</a> | <a href="/entries/new">➕ New Entry</a></nav>
    <h1>${title}</h1>
    ${body}
</body>
</html>`;

// Routes

// GET /entries - List all entries
app.get('/entries', (req, res) => {
    db.all("SELECT id, title FROM entries", [], (err, rows) => {
        if (err) return res.status(500).send("Internal Server Error");
        
        let listHtml = rows.length === 0 ? "<p>No entries found.</p>" : "<ul>";
        rows.forEach(row => {
            listHtml += `<li><a href="/entries/${row.id}">${row.title}</a></li>`;
        });
        if (rows.length > 0) listHtml += "</ul>";
        
        res.send(renderLayout("Wiki Entries", listHtml));
    });
});

// Page to create a new entry (UI)
app.get('/entries/new', (req, res) => {
    const form = `
        <form action="/entries" method="POST">
            <input type="text" name="title" placeholder="Entry Title" required>
            <textarea name="content" placeholder="Content..." required></textarea>
            <input type="text" name="createdBy" placeholder="Your Name" required>
            <button type="submit">Create Entry</button>
        </form>
    `;
    res.send(renderLayout("Create New Entry", form));
});

// POST /entries - Create a new entry
app.post('/entries', (req, res) => {
    const { title, content, createdBy } = req.body;
    if (!title || !content || !createdBy) return res.status(400).json({ error: "Missing fields" });

    const id = uuidv4();
    const now = new Date().toISOString();

    db.run("INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)", 
        [id, title, content, createdBy, now], function(err) {
        if (err) return res.status(500).json({ error: err.message });

        db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            [id, content, createdBy, "Initial creation", now], (err) => {
            res.status(201).json({ id, title, content, lastModifiedBy: createdBy, lastModifiedAt: now });
        });
    });
});

// GET /entries/{entryId} - View specific entry
app.get('/entries/:entryId', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (err) return res.status(500).send("Internal Server Error");
        if (!row) return res.status(404).send("Entry not found");

        const contentHtml = `
            <div class="entry-card">
                <p>${row.content}</p>
                <hr>
                <small>Last modified by ${row.lastModifiedBy} on ${row.lastModifiedAt}</small>
            </div>
            <div style="margin-top: 20px;">
                <a href="/entries/${row.id}/edit">✏️ Edit this page</a> | 
                <a href="/entries/${row.id}/edits">📜 View History</a>
            </div>
        `;
        res.send(renderLayout(row.title, contentHtml));
    });
});

// Page to edit an entry (UI)
app.get('/entries/:entryId/edit', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).send("Entry not found");
        
        const form = `
            <form action="/entries/${row.id}" method="POST">
                <input type="hidden" name="_method" value="PUT">
                <textarea name="content" required>${row.content}</textarea>
                <input type="text" name="modifiedBy" placeholder="Your Name" required>
                <input type="text" name="summary" placeholder="What did you change?" required>
                <button type="submit">Save Changes</button>
            </form>
        `;
        res.send(renderLayout(`Editing: ${row.title}`, form));
    });
});

// PUT /entries/{entryId} - Update entry
// Since HTML forms only support GET/POST, we check for a hidden _method field or use a custom route
app.post('/entries/:entryId', (req, res) => {
    if (req.body._method === 'PUT') {
        const { entryId } = req.params;
        const { content, modifiedBy, summary } = req.body;
        const now = new Date().toISOString();

        if (!content || !modifiedBy || !summary) return res.status(400).json({ error: "Missing fields" });

        db.run("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
            [content, modifiedBy, now, entryId], function(err) {
            if (err || this.changes === 0) return res.status(404).json({ error: "Entry not found" });

            db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
                [entryId, content, modifiedBy, summary, now], (err) => {
                res.redirect(`/entries/${entryId}`);
            });
        });
    } else {
        res.status(405).send("Method Not Allowed");
    }
});

// GET /entries/{entryId}/edits - History
app.get('/entries/:entryId/edits', (req, res) => {
    const { entryId } = req.params;
    db.get("SELECT title FROM entries WHERE id = ?", [entryId], (err, entry) => {
        if (!entry) return res.status(404).send("Entry not found");

        db.all("SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", [entryId], (err, rows) => {
            if (err) return res.status(500).send("Internal Server Error");

            let historyHtml = "<h3>Edit History</h3>";
            rows.forEach((edit, index) => {
                historyHtml += `
                    <div class="entry-card">
                        <strong>${edit.modifiedBy}</strong> - ${edit.modifiedAt}<br>
                        <em>Summary: ${edit.summary}</em>
                        <div class="diff-box">${edit.content}</div>
                    </div>
                `;
            });
            res.send(renderLayout(`History: ${entry.title}`, historyHtml));
        });
    });
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Wiki server running on http://0.0.0.0:5000');
});