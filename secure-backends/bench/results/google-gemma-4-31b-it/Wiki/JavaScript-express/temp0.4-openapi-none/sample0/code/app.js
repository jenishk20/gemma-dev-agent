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
const renderHTML = (title, content) => `
    <!DOCTYPE html>
    <html>
    <head>
        <title>${title}</title>
        <style>
            body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav { margin-bottom: 20px; }
            .entry-link { display: block; margin: 10px 0; font-size: 18px; text-decoration: none; color: #007bff; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="text"], textarea { width: 100%; padding: 8px; box-sizing: border-box; }
            textarea { height: 200px; }
            button { padding: 10px 20px; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; }
            .meta { color: #666; font-size: 0.9em; margin-bottom: 20px; }
            .diff { background: #eee; padding: 10px; border-left: 4px solid #ccc; margin: 10px 0; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <div class="nav"><a href="/entries">🏠 Home</a></div>
        <div class="card">${content}</div>
    </body>
    </html>
`;

// Routes

// GET /entries - List all entries
app.get('/entries', (req, res) => {
    db.all("SELECT id, title FROM entries", [], (err, rows) => {
        if (err) return res.status(500).send(err.message);
        
        let listHtml = `<h1>Wiki Entries</h1>`;
        listHtml += `<a href="/entries/new" style="margin-bottom: 20px; display: inline-block; color: green;">+ Create New Entry</a><hr>`;
        
        if (rows.length === 0) {
            listHtml += `<p>No entries found.</p>`;
        } else {
            rows.forEach(row => {
                listHtml += `<a class="entry-link" href="/entries/${row.id}">${row.title}</a>`;
            });
        }
        res.send(renderHTML("Wiki Home", listHtml));
    });
});

// Page to create new entry (Frontend helper)
app.get('/entries/new', (req, res) => {
    const html = `
        <h1>Create New Entry</h1>
        <form action="/entries" method="POST">
            <div class="form-group">
                <label>Title</label>
                <input type="text" name="title" required>
            </div>
            <div class="form-group">
                <label>Content</label>
                <textarea name="content" required></textarea>
            </div>
            <div class="form-group">
                <label>Your Name</label>
                <input type="text" name="createdBy" required>
            </div>
            <button type="submit">Save Entry</button>
        </form>
    `;
    res.send(renderHTML("New Entry", html));
});

// POST /entries - Create entry
app.post('/entries', (req, res) => {
    const { title, content, createdBy } = req.body;
    if (!title || !content || !createdBy) return res.status(400).json({ error: "Missing fields" });

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

// GET /entries/{id} - View entry
app.get('/entries/:entryId', (req, res) => {
    const entryId = req.params.entryId;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (err) return res.status(500).send(err.message);
        if (!row) return res.status(404).send("Entry not found");

        const html = `
            <h1>${row.title}</h1>
            <div class="meta">Last edited by ${row.lastModifiedBy} on ${row.lastModifiedAt}</div>
            <div style="white-space: pre-wrap; margin-bottom: 20px;">${row.content}</div>
            <hr>
            <div style="display: flex; gap: 10px;">
                <a href="/entries/${row.id}/edit">✏️ Edit Page</a>
                <a href="/entries/${row.id}/edits">📜 History</a>
            </div>
        `;
        res.send(renderHTML(row.title, html));
    });
});

// Page to edit entry (Frontend helper)
app.get('/entries/:entryId/edit', (req, res) => {
    const entryId = req.params.entryId;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).send("Entry not found");
        const html = `
            <h1>Editing: ${row.title}</h1>
            <form action="/entries/${row.id}" method="POST">
                <div class="form-group">
                    <label>Content</label>
                    <textarea name="content" required>${row.content}</textarea>
                </div>
                <div class="form-group">
                    <label>Your Name</label>
                    <input type="text" name="modifiedBy" required>
                </div>
                <div class="form-group">
                    <label>Edit Summary (What did you change?)</label>
                    <input type="text" name="summary" required>
                </div>
                <button type="submit">Save Changes</button>
            </form>
        `;
        res.send(renderHTML("Edit Entry", html));
    });
});

// PUT/POST /entries/{id} - Update entry
// Using POST for the HTML form compatibility, but mapping to the PUT logic
app.post('/entries/:entryId', (req, res) => {
    const entryId = req.params.entryId;
    const { content, modifiedBy, summary } = req.body;
    const now = new Date().toISOString();

    if (!content || !modifiedBy || !summary) return res.status(400).json({ error: "Missing fields" });

    db.get("SELECT id FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).json({ error: "Entry not found" });

        db.serialize(() => {
            db.run("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
                [content, modifiedBy, now, entryId]);
            db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)", 
                [entryId, content, modifiedBy, summary, now]);
        });

        res.redirect(`/entries/${entryId}`);
    });
});

// GET /entries/{id}/edits - History
app.get('/entries/:entryId/edits', (req, res) => {
    const entryId = req.params.entryId;
    db.get("SELECT title FROM entries WHERE id = ?", [entryId], (err, entry) => {
        if (!entry) return res.status(404).send("Entry not found");

        db.all("SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", [entryId], (err, rows) => {
            if (err) return res.status(500).send(err.message);

            let historyHtml = `<h1>Revision History: ${entry.title}</h1>`;
            if (rows.length === 0) {
                historyHtml += `<p>No edits found.</p>`;
            } else {
                rows.forEach((edit, index) => {
                    historyHtml += `
                        <div class="card" style="margin-bottom: 15px; background: #fafafa;">
                            <strong>${edit.modifiedBy}</strong> - ${edit.modifiedAt}<br>
                            <em>"${edit.summary}"</em>
                            <div class="diff">${edit.content}</div>
                        </div>
                    `;
                });
            }
            res.send(renderHTML(`History: ${entry.title}`, historyHtml));
        });
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Wiki server running at http://0.0.0.0:${port}`);
});