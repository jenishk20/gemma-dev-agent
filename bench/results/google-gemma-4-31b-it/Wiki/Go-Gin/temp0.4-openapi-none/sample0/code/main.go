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
	ID          int
	Contributor string
	Summary     string
	Content     string
	CreatedAt   time.Time
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
		contributor TEXT,
		summary TEXT,
		content TEXT,
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
	r.SetHTMLTemplate(template.Must(template.New("").Parse(`
{{define "list"}}
	<h1>Wiki Entries</h1>
	<ul>
	{{range .}}
		<li><a href="/entries/{{.ID}}">{{.Title}}</a></li>
	{{end}}
	</ul>
	<hr>
	<h3>Create New Entry</h3>
	<form action="/entries" method="post">
		<input type="text" name="title" placeholder="Title" required><br>
		<textarea name="content" placeholder="Content" required></textarea><br>
		<input type="text" name="createdBy" placeholder="Your Name" required><br>
		<button type="submit">Create</button>
	</form>
{{end}}

{{define "entry"}}
	<h1>{{.Entry.Title}}</h1>
	<p>{{.Entry.Content}}</p>
	<p><small>Last modified by {{.Entry.LastModifiedBy}} on {{.Entry.LastModifiedAt.Format "2006-01-02 15:04"}}</small></p>
	<hr>
	<h3>Edit Entry</h3>
	<form action="/entries/{{.Entry.ID}}" method="put">
		<textarea name="content" required>{{.Entry.Content}}</textarea><br>
		<input type="text" name="modifiedBy" placeholder="Your Name" required><br>
		<input type="text" name="summary" placeholder="Edit Summary" required><br>
		<button type="submit">Update</button>
	</form>
	<p><a href="/entries/{{.Entry.ID}}/edits">View History</a> | <a href="/entries">Back to List</a></p>
{{end}}

{{define "history"}}
	<h1>History for {{.Title}}</h1>
	<ul>
	{{range .Edits}}
		<li>
			<strong>{{.Contributor}}</strong> ({{.CreatedAt.Format "2006-01-02 15:04"}}): {{.Summary}}<br>
			<pre style="background: #eee; padding: 5px;">{{.Content}}</pre>
		</li>
	{{end}}
	</ul>
	<a href="/entries">Back to List</a>
{{end}}
`)))

	// GET /entries
	r.GET("/entries", func(c *gin.Context) {
		rows, err := db.Query("SELECT id, title, content, last_modified_by, last_modified_at FROM entries")
		if err != nil {
			c.String(http.StatusInternalServerError, err.Error())
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

	// POST /entries
	r.POST("/entries", func(c *gin.Context) {
		var ne NewEntry
		// Since we use HTML forms for the webapp part, we bind from form
		if err := c.ShouldBindQuery(&ne); err != nil {
			// Fallback to form binding
			c.Request.ParseForm()
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
		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.CreatedBy, "Initial creation", ne.Content, now)

		c.JSON(http.StatusCreated, Entry{ID: id, Title: ne.Title, Content: ne.Content, LastModifiedBy: ne.CreatedBy, LastModifiedAt: now})
	})

	// GET /entries/{entryId}
	r.GET("/entries/:entryId", func(c *gin.Context) {
		id := c.Param("entryId")
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		if err != nil {
			c.String(http.StatusNotFound, "Entry not found")
			return
		}
		c.HTML(http.StatusOK, "entry", gin.H{"Entry": e})
	})

	// PUT /entries/{entryId}
	r.PUT("/entries/:entryId", func(c *gin.Context) {
		id := c.Param("entryId")
		var ue UpdateEntry
		
		// Support both JSON and Form for PUT (Gin doesn't bind PUT forms automatically)
		if c.GetHeader("Content-Type") == "application/json" {
			if err := c.ShouldBindJSON(&ue); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}
		} else {
			c.Request.ParseForm()
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

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, ue.ModifiedBy, ue.Summary, ue.Content, now)

		var e Entry
		db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)

		c.JSON(http.StatusOK, e)
	})

	// GET /entries/{entryId}/edits
	r.GET("/entries/:entryId/edits", func(c *gin.Context) {
		id := c.Param("entryId")
		var title string
		err := db.QueryRow("SELECT title FROM entries WHERE id = ?", id).Scan(&title)
		if err != nil {
			c.String(http.StatusNotFound, "Entry not found")
			return
		}

		rows, err := db.Query("SELECT contributor, summary, content, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", id)
		if err != nil {
			c.String(http.StatusInternalServerError, err.Error())
			return
		}
		defer rows.Close()

		var edits []EditHistory
		for rows.Next() {
			var eh EditHistory
			rows.Scan(&eh.Contributor, &eh.Summary, &eh.Content, &eh.CreatedAt)
			edits = append(edits, eh)
		}
		c.HTML(http.StatusOK, "history", gin.H{"Title": title, "Edits": edits})
	})

	r.Run("0.0.0.0:5000")
}