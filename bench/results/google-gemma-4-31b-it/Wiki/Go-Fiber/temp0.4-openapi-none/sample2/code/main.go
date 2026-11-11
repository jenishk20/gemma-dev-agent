package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/gofiber/fiber/v2"
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
	Title     string `json:"title"`
	Content   string `json:"content"`
	CreatedBy string `json:"createdBy"`
}

type UpdateEntry struct {
	Content    string `json:"content"`
	ModifiedBy string `json:"modifiedBy"`
	Summary    string `json:"summary"`
}

type EditHistory struct {
	ID        int
	EntryID   string
	User      string
	Summary   string
	Content   string
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
		user TEXT,
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
	app := fiber.New()

	// GET /entries - List all entries
	app.Get("/entries", func(c *fiber.Ctx) error {
		rows, err := db.Query("SELECT id, title FROM entries")
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}
		defer rows.Close()

		html := "<h1>Wiki Entries</h1><ul>"
		for rows.Next() {
			var id, title string
			rows.Scan(&id, &title)
			html += fmt.Sprintf("<li><a href='/entries/%s'>%s</a></li>", id, title)
		}
		html += "</ul><br><a href='/create'>Create New Entry</a>"
		c.Set("Content-Type", "text/html")
		return c.SendString(html)
	})

	// POST /entries - Create new entry
	app.Post("/entries", func(c *fiber.Ctx) error {
		var req NewEntry
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
		}

		id := uuid.New().String()
		now := time.Now()

		tx, err := db.Begin()
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}

		_, err = tx.Exec("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
			id, req.Title, req.Content, req.CreatedBy, now)
		if err != nil {
			tx.Rollback()
			return c.Status(500).SendString(err.Error())
		}

		_, err = tx.Exec("INSERT INTO edits (entry_id, user, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.CreatedBy, "Initial creation", req.Content, now)
		if err != nil {
			tx.Rollback()
			return c.Status(500).SendString(err.Error())
		}

		tx.Commit()

		return c.Status(http.StatusCreated).JSON(Entry{
			ID:             id,
			Title:          req.Title,
			Content:        req.Content,
			LastModifiedBy: req.CreatedBy,
			LastModifiedAt: now,
		})
	})

	// GET /entries/{entryId} - Get specific entry
	app.Get("/entries/:entryId", func(c *fiber.Ctx) error {
		id := c.Params("entryId")
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)

		if err == sql.ErrNoRows {
			return c.Status(404).SendString("Entry not found")
		} else if err != nil {
			return c.Status(500).SendString(err.Error())
		}

		html := fmt.Sprintf("<h1>%s</h1><p><i>Last edited by %s on %s</i></p><div>%s</div>",
			e.Title, e.LastModifiedBy, e.LastModifiedAt.Format(time.RFC1123), e.Content)
		html += fmt.Sprintf("<br><br><a href='/entries/%s/edits'>View History</a> | <a href='/edit/%s'>Edit Entry</a>", id, id)
		html += "<br><a href='/entries'>Back to Home</a>"

		c.Set("Content-Type", "text/html")
		return c.SendString(html)
	})

	// PUT /entries/{entryId} - Update entry
	app.Put("/entries/:entryId", func(c *fiber.Ctx) error {
		id := c.Params("entryId")
		var req UpdateEntry
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
		}

		var title string
		err := db.QueryRow("SELECT title FROM entries WHERE id = ?", id).Scan(&title)
		if err == sql.ErrNoRows {
			return c.Status(404).JSON(fiber.Map{"error": "Entry not found"})
		}

		now := time.Now()
		tx, err := db.Begin()
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}

		_, err = tx.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			req.Content, req.ModifiedBy, now, id)
		if err != nil {
			tx.Rollback()
			return c.Status(500).SendString(err.Error())
		}

		_, err = tx.Exec("INSERT INTO edits (entry_id, user, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.ModifiedBy, req.Summary, req.Content, now)
		if err != nil {
			tx.Rollback()
			return c.Status(500).SendString(err.Error())
		}

		tx.Commit()

		return c.JSON(Entry{
			ID:             id,
			Title:          title,
			Content:        req.Content,
			LastModifiedBy: req.ModifiedBy,
			LastModifiedAt: now,
		})
	})

	// GET /entries/{entryId}/edits - History
	app.Get("/entries/:entryId/edits", func(c *fiber.Ctx) error {
		id := c.Params("entryId")
		
		// Check if entry exists
		var exists int
		db.QueryRow("SELECT 1 FROM entries WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			return c.Status(404).SendString("Entry not found")
		}

		rows, err := db.Query("SELECT user, summary, content, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", id)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}
		defer rows.Close()

		html := fmt.Sprintf("<h1>Edit History for %s</h1><hr>", id)
		for rows.Next() {
			var user, summary, content string
			var createdAt time.Time
			rows.Scan(&user, &summary, &content, &createdAt)
			html += fmt.Sprintf("<div><b>%s</b> (%s) - %s<br><pre>%s</pre><hr></div>",
				user, createdAt.Format(time.RFC1123), summary, content)
		}
		html += "<br><a href='/entries'>Back to Home</a>"

		c.Set("Content-Type", "text/html")
		return c.SendString(html)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}