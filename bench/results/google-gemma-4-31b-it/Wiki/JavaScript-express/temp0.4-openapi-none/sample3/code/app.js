const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const app = express();
const port = 5000;
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

// Helper to render basic HTML wrappers
const wrapHtml = (content) => `
<!DOCTYPE html>
<html>
<head>
    <title>Wiki WebApp</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .entry-link { display: block; margin: 10px 0; font-size: 18px; text-decoration: none; color: #007bff; }
        .meta { font-size: 0.8em; color: #666; margin-bottom: 20px; }
        .edit-item { border-bottom: 1px solid #eee; padding: 10px 0; }
        .diff-old { color: red; text-decoration: line-through; }
        .diff-new { color: green; font-weight: bold; }
        textarea { width: 100%; height: 200px; margin: 10px 0; }
        input { display: block; margin: 10px 0; width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #28a745; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <nav><a href="/entries">🏠 Home</a></nav>
        <hr>
        ${content}
    </div>
</body>
</html>`;

// GET /entries - List all entries
app.get('/entries', (req, res) => {
    db.all("SELECT id, title FROM entries", [], (err, rows) => {
        if (err) return res.status(500).send(err.message);
        
        let listHtml = "<h1>Wiki Entries</h1>";
        listHtml += `<a href="/entries/new" style="margin-bottom: 20px; display: inline-block;">+ Create New Entry</a><br>`;
        
        if (rows.length === 0) {
            listHtml += "<p>No entries found.</p>";
        } else {
            rows.forEach(row => {
                listHtml += `<a class="entry-link" href="/entries/${row.id}">${row.title}</a>`;
            });
        }
        res.send(wrapHtml(listHtml));
    });
});

// POST /entries - Create new entry
app.post('/entries', (req, res) => {
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
        
        res.status(201).json({ id, title, content, lastModifiedBy: createdBy, lastModifiedAt: now });
    });
});

// GET /entries/{entryId} - View entry
app.get('/entries/:entryId', (req, res) => {
    const entryId = req.params.entryId;

    // Handle the "new" page for UI convenience
    if (entryId === 'new') {
        let formHtml = `
            <h1>Create Entry</h1>
            <form action="/entries" method="POST">
                <input type="text" name="title" placeholder="Title" required>
                <input type="text" name="createdBy" placeholder="Your Name" required>
                <textarea name="content" placeholder="Content" required></textarea>
                <button type="submit">Save Entry</button>
            </form>
        `;
        return res.send(wrapHtml(formHtml));
    }

    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (err) return res.status(500).send(err.message);
        if (!row) return res.status(404).send(wrapHtml("<h1>404 Not Found</h1><p>Entry not found.</p>"));

        let contentHtml = `
            <h1>${row.title}</h1>
            <div class="meta">Last modified by ${row.lastModifiedBy} on ${row.lastModifiedAt}</div>
            <div style="white-space: pre-wrap;">${row.content}</div>
            <hr>
            <a href="/entries/${row.id}/edit">Edit this page</a> | 
            <a href="/entries/${row.id}/edits">View History</a>
        `;
        res.send(wrapHtml(contentHtml));
    });
});

// UI helper for editing
app.get('/entries/:entryId/edit', (req, res) => {
    const entryId = req.params.entryId;
    db.get("SELECT * FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).send("Not Found");
        let formHtml = `
            <h1>Edit: ${row.title}</h1>
            <form action="/entries/${row.id}" method="POST" style="display:flex; flex-direction:column">
                <input type="hidden" name="_method" value="PUT">
                <input type="text" name="modifiedBy" placeholder="Your Name" required>
                <input type="text" name="summary" placeholder="What did you change?" required>
                <textarea name="content" required>${row.content}</textarea>
                <button type="submit">Save Changes</button>
            </form>
        `;
        // Since HTML forms only support GET/POST, we'll handle the PUT via a POST with a hidden field or a separate route.
        // For this implementation, we'll use a POST route that mimics PUT.
        res.send(wrapHtml(formHtml));
    });
});

// PUT /entries/{entryId} - Update entry
// We implement both PUT (API) and POST (for the HTML form)
app.post('/entries/:entryId', (req, res) => {
    // This is a helper for the HTML form to simulate PUT
    const entryId = req.params.entryId;
    const { content, modifiedBy, summary } = req.body;
    
    if (!content || !modifiedBy || !summary) {
        return res.status(400).send("Missing fields");
    }

    const now = new Date().toISOString();
    db.serialize(() => {
        db.run("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
            [content, modifiedBy, now, entryId], function(err) {
            if (err || this.changes === 0) return res.status(404).send("Entry not found");
            
            db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)", 
                [entryId, content, modifiedBy, summary, now], () => {
                res.redirect(`/entries/${entryId}`);
            });
        });
    });
});

app.put('/entries/:entryId', (req, res) => {
    const entryId = req.params.entryId;
    const { content, modifiedBy, summary } = req.body;
    if (!content || !modifiedBy || !summary) return res.status(400).json({ error: "Missing fields" });

    const now = new Date().toISOString();
    db.serialize(() => {
        db.run("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
            [content, modifiedBy, now, entryId], function(err) {
            if (err || this.changes === 0) return res.status(404).json({ error: "Not found" });
            
            db.run("INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)", 
                [entryId, content, modifiedBy, summary, now], () => {
                res.json({ id: entryId, content, lastModifiedBy: modifiedBy, lastModifiedAt: now });
            });
        });
    });
});

// GET /entries/{entryId}/edits - View history
app.get('/entries/:entryId/edits', (req, res) => {
    const entryId = req.params.entryId;
    
    db.get("SELECT id FROM entries WHERE id = ?", [entryId], (err, row) => {
        if (!row) return res.status(404).send(wrapHtml("<h1>404 Not Found</h1>"));

        db.all("SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", [entryId], (err, edits) => {
            let historyHtml = `<h1>Edit History</h1>`;
            
            for (let i = 0; i < edits.length; i++) {
                const current = edits[i];
                const previous = edits[i + 1] || { content: "" };
                
                historyHtml += `
                    <div class="edit-item">
                        <strong>${current.modifiedBy}</strong> (${current.modifiedAt})<br>
                        <em>Summary: ${current.summary}</em><br>
                        <div style="background: #eee; padding: 5px; font-family: monospace; font-size: 12px;">
                            <span class="diff-old">${previous.content.substring(0, 100)}...</span><br>
                            <span class="diff-new">${current.content.substring(0, 100)}...</span>
                        </div>
                    </div>`;
            }
            res.send(wrapHtml(historyHtml));
        });
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Wiki server running at http://0.0.0.0:${port}`);
});