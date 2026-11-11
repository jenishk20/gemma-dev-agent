package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

// Models
type Entry struct {
	ID             string    `json:"id"`
	Title          string    `json:"title"`
	Content        string    `json:"content"`
	LastModifiedBy string    `json:"lastModifiedBy"`
	LastModifiedAt time.Time `json:"lastModifiedAt"`
}

type NewEntry struct {
	Title     string `json:"title" binding:"required"`
	Content   string `json:"content" binding:"required"`
	CreatedBy string `json:"createdBy" binding:"required"`
}

type UpdateEntry struct {
	Content    string `json:"content" binding:"required"`
	ModifiedBy string `json:"modifiedBy" binding:"required"`
	Summary    string `json:"summary" binding:"required"`
}

type EditHistory struct {
	ID        int
	EntryID   string
	Content   string
	User      string
	Summary   string
	CreatedAt time.Time
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS entries (
		id TEXT PRIMARY KEY,
		title TEXT,
		content TEXT,
		last_modified_by TEXT,
		last_modified_at DATETIME
	);
	CREATE TABLE IF NOT EXISTS edits (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		entry_id TEXT,
		content TEXT,
		user TEXT,
		summary TEXT,
		created_at DATETIME,
		FOREIGN KEY(entry_id) REFERENCES entries(id)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	// HTML Templates
	templates := template.Must(template.New("wiki").Parse(`
		{{define "list"}}
		<h1>Wiki Entries</h1>
		<ul>
		{{range .}}
			<li><a href="/entries/{{.ID}}">{{.Title}}</a></li>
		{{end}}
		</ul>
		<hr>
		<h3>Create New Entry</h3>
		<form action="/entries" method="POST">
			<input type="text" name="title" placeholder="Title" required><br>
			<textarea name="content" placeholder="Content" required></textarea><br>
			<input type="text" name="createdBy" placeholder="Your Name" required><br>
			<button type="submit">Create</button>
		</form>
		{{end}}

		{{define "entry"}}
		<h1>{{.Title}}</h1>
		<p>Last modified by {{.LastModifiedBy}} on {{.LastModifiedAt.Format "2006-01-02 15:04"}}</p>
		<div style="border: 1px solid #ccc; padding: 10px; white-space: pre-wrap;">{{.Content}}</div>
		<hr>
		<a href="/entries/{{.ID}}/edits">View History</a> | <a href="/entries">Back to List</a>
		<h3>Edit Entry</h3>
		<form action="/entries/{{.ID}}" method="PUT">
			<textarea name="content" required>{{.Content}}</textarea><br>
			<input type="text" name="modifiedBy" placeholder="Your Name" required><br>
			<input type="text" name="summary" placeholder="What did you change?" required><br>
			<button type="submit">Save Changes</button>
		</form>
		{{end}}

		{{define "history"}}
		<h1>Edit History</h1>
		<a href="/entries">Back to List</a> | <a href="/entries/{{.EntryID}}">Back to Entry</a>
		<hr>
		{{range .Edits}}
			<div style="border-bottom: 1px solid #eee; margin-bottom: 10px;">
				<strong>{{.User}}</strong> - {{.CreatedAt.Format "2006-01-02 15:04"}}<br>
				<em>Summary: {{.Summary}}</em><br>
				<pre style="background: #f4f4f4; padding: 5px;">{{.Content}}</pre>
			</div>
		{{end}}
		{{end}}
	`))

	r.HTMLRender = gin.WrapHTML(templates)

	// GET /entries - List entries
	r.GET("/entries", func(c *gin.Context) {
		rows, err := db.Query("SELECT id, title, content, last_modified_by, last_modified_at FROM entries")
		if err != nil {
			c.String(http.StatusInternalServerError, "DB Error")
			return
		}
		defer rows.Close()

		var entries []Entry
		for rows.Next() {
			var e Entry
			rows.Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
			entries = append(entries, e)
		}
		c.HTML(http.StatusOK, "list", entries)
	})

	// POST /entries - Create entry
	r.POST("/entries", func(c *gin.Context) {
		var ne NewEntry
		if err := c.ShouldBindJSON(&ne); err != nil {
			// Fallback for HTML form submission
			ne.Title = c.PostForm("title")
			ne.Content = c.PostForm("content")
			ne.CreatedBy = c.PostForm("createdBy")
		}

		id := uuid.New().String()
		now := time.Now()
		_, err := db.Exec("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.Title, ne.Content, ne.CreatedBy, now)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		_, err = db.Exec("INSERT INTO edits (entry_id, content, user, summary, created_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.Content, ne.CreatedBy, "Initial creation", now)

		c.JSON(http.StatusCreated, Entry{ID: id, Title: ne.Title, Content: ne.Content, LastModifiedBy: ne.CreatedBy, LastModifiedAt: now})
	})

	// GET /entries/{entryId} - View entry
	r.GET("/entries/:entryId", func(c *gin.Context) {
		id := c.Param("entryId")
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		if err == sql.ErrNoRows {
			c.String(http.StatusNotFound, "Entry not found")
			return
		} else if err != nil {
			c.String(http.StatusInternalServerError, "DB Error")
			return
		}
		c.HTML(http.StatusOK, "entry", e)
	})

	// PUT /entries/{entryId} - Update entry
	r.PUT("/entries/:entryId", func(c *gin.Context) {
		id := c.Param("entryId")
		var ue UpdateEntry
		if err := c.ShouldBindJSON(&ue); err != nil {
			// Fallback for HTML form submission (Gin doesn't natively support PUT from HTML forms, 
			// but we handle it via JSON or custom logic)
			ue.Content = c.PostForm("content")
			ue.ModifiedBy = c.PostForm("modifiedBy")
			ue.Summary = c.PostForm("summary")
		}

		now := time.Now()
		res, err := db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			ue.Content, ue.ModifiedBy, now, id)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		count, _ := res.RowsAffected()
		if count == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Entry not found"})
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, content, user, summary, created_at) VALUES (?, ?, ?, ?, ?)",
			id, ue.Content, ue.ModifiedBy, ue.Summary, now)

		var e Entry
		db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)

		c.JSON(http.StatusOK, e)
	})

	// GET /entries/{entryId}/edits - View history
	r.GET("/entries/:entryId/edits", func(c *gin.Context) {
		id := c.Param("entryId")
		var exists int
		db.QueryRow("SELECT 1 FROM entries WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			c.String(http.StatusNotFound, "Entry not found")
			return
		}

		rows, err := db.Query("SELECT id, entry_id, content, user, summary, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", id)
		if err != nil {
			c.String(http.StatusInternalServerError, "DB Error")
			return
		}
		defer rows.Close()

		var edits []EditHistory
		for rows.Next() {
			var eh EditHistory
			rows.Scan(&eh.ID, &eh.EntryID, &eh.Content, &eh.User, &eh.Summary, &eh.CreatedAt)
			edits = append(edits, eh)
		}

		c.HTML(http.StatusOK, "history", gin.H{
			"EntryID": id,
			"Edits":   edits,
		})
	})

	// Handle HTML form PUT simulation (since HTML forms only do GET/POST)
	r.POST("/entries/:entryId", func(c *gin.Context) {
		// This is a helper for the HTML form to simulate PUT
		c.Request.Method = http.MethodPut
		// We can't call another handler directly easily in Gin without a wrapper, 
		// so we just implement the logic or use a redirect. 
		// For simplicity in this single-file app, we'll just handle the update here.
		id := c.Param("entryId")
		content := c.PostForm("content")
		user := c.PostForm("modifiedBy")
		summary := c.PostForm("summary")
		
		now := time.Now()
		db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?", content, user, now, id)
		db.Exec("INSERT INTO edits (entry_id, content, user, summary, created_at) VALUES (?, ?, ?, ?, ?)", id, content, user, summary, now)
		
		c.Redirect(http.StatusSeeOther, "/entries/"+id)
	})

	r.Run("0.0.0.0:5000")
}