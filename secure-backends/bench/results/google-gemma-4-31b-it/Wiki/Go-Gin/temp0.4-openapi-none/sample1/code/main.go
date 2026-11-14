package main

import (
	"database/sql"
	"fmt"
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
	ID         int
	EntryID    string
	Contributor string
	Summary    string
	Content    string
	CreatedAt   time.Time
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	createEntries := `CREATE TABLE IF NOT EXISTS entries (
		id TEXT PRIMARY KEY,
		title TEXT,
		content TEXT,
		last_modified_by TEXT,
		last_modified_at DATETIME
	);`
	createEdits := `CREATE TABLE IF NOT EXISTS edits (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		entry_id TEXT,
		contributor TEXT,
		summary TEXT,
		content TEXT,
		created_at DATETIME,
		FOREIGN KEY(entry_id) REFERENCES entries(id)
	);`

	_, err = db.Exec(createEntries)
	if err != nil {
		log.Fatal(err)
	}
	_, err = db.Exec(createEdits)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	r.GET("/entries", func(c *gin.Context) {
		rows, err := db.Query("SELECT id, title FROM entries")
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}
		defer rows.Close()

		html := "<h1>Wiki Entries</h1><ul>"
		for rows.Next() {
			var id, title string
			rows.Scan(&id, &title)
			html += fmt.Sprintf("<li><a href='/entries/%s'>%s</a></li>", id, title)
		}
		html += "</ul><hr><a href='/create'>Create New Entry</a>"
		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html)
	})

	r.POST("/entries", func(c *gin.Context) {
		var req NewEntry
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		id := uuid.New().String()
		now := time.Now()

		_, err := db.Exec("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
			id, req.Title, req.Content, req.CreatedBy, now)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.CreatedBy, "Initial creation", req.Content, now)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusCreated, Entry{
			ID:             id,
			Title:          req.Title,
			Content:        req.Content,
			LastModifiedBy: req.CreatedBy,
			LastModifiedAt: now,
		})
	})

	r.GET("/entries/:entryId", func(c *gin.Context) {
		id := c.Param("entryId")
		var entry Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&entry.ID, &entry.Title, &entry.Content, &entry.LastModifiedBy, &entry.LastModifiedAt)

		if err == sql.ErrNoRows {
			c.String(http.StatusNotFound, "Entry not found")
			return
		} else if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}

		rows, err := db.Query("SELECT contributor FROM edits WHERE entry_id = ?", id)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}
		defer rows.Close()

		contributors := make(map[string]bool)
		for rows.Next() {
			var name string
			rows.Scan(&name)
			contributors[name] = true
		}

		contribList := ""
		for name := range contributors {
			contribList += name + ", "
		}

		html := fmt.Sprintf("<h1>%s</h1><p>%s</p><hr><p>Last edited by: %s at %s</p><p>Contributors: %s</p>",
			entry.Title, entry.Content, entry.LastModifiedBy, entry.LastModifiedAt.Format(time.RFC1123), contribList)
		html += fmt.Sprintf("<br><a href='/entries/%s/edits'>View History</a>", id)
		
		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html)
	})

	r.PUT("/entries/:entryId", func(c *gin.Context) {
		id := c.Param("entryId")
		var req UpdateEntry
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		now := time.Now()
		res, err := db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			req.Content, req.ModifiedBy, now, id)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		rowsAffected, _ := res.RowsAffected()
		if rowsAffected == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Entry not found"})
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.ModifiedBy, req.Summary, req.Content, now)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		var entry Entry
		db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&entry.ID, &entry.Title, &entry.Content, &entry.LastModifiedBy, &entry.LastModifiedAt)

		c.JSON(http.StatusOK, entry)
	})

	r.GET("/entries/:entryId/edits", func(c *gin.Context) {
		id := c.Param("entryId")
		
		var exists bool
		db.QueryRow("SELECT EXISTS(SELECT 1 FROM entries WHERE id=?)", id).Scan(&exists)
		if !exists {
			c.String(http.StatusNotFound, "Entry not found")
			return
		}

		rows, err := db.Query("SELECT contributor, summary, content, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", id)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}
		defer rows.Close()

		html := fmt.Sprintf("<h1>Edit History for %s</h1><table border='1'><tr><th>Contributor</th><th>Summary</th><th>Content</th><th>Date</th></tr>", id)
		for rows.Next() {
			var contributor, summary, content string
			var createdAt time.Time
			rows.Scan(&contributor, &summary, &content, &createdAt)
			html += fmt.Sprintf("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>", 
				contributor, summary, content, createdAt.Format(time.RFC1123))
		}
		html += "</table><br><a href='/entries/"+id+"'>Back to Entry</a>"

		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html)
	})

	r.Run("0.0.0.0:5000")
}