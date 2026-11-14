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

type Edit struct {
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
		html += "</ul><br><a href='/'>Home</a>"
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
		_, err := db.Exec("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
			id, req.Title, req.Content, req.CreatedBy, now)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, content, user, summary, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.Content, req.CreatedBy, "Initial creation", now)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		return c.Status(201).JSON(Entry{
			ID:             id,
			Title:          req.Title,
			Content:        req.Content,
			LastModifiedBy: req.CreatedBy,
			LastModifiedAt: now,
		})
	})

	// GET /entries/{entryId} - View entry
	app.Get("/entries/:entryId", func(c *fiber.Ctx) error {
		id := c.Params("entryId")
		var entry Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&entry.ID, &entry.Title, &entry.Content, &entry.LastModifiedBy, &entry.LastModifiedAt)

		if err == sql.ErrNoRows {
			return c.Status(404).SendString("Entry not found")
		} else if err != nil {
			return c.Status(500).SendString(err.Error())
		}

		html := fmt.Sprintf("<h1>%s</h1><p>%s</p><hr>", entry.Title, entry.Content)
		html += fmt.Sprintf("<p>Last edited by %s on %s</p>", entry.LastModifiedBy, entry.LastModifiedAt.Format(time.RFC1123))
		html += fmt.Sprintf("<div><a href='/entries/%s/edits'>View History</a> | <a href='/entries'>Back to List</a></div>", id)
		
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

		now := time.Now()
		res, err := db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			req.Content, req.ModifiedBy, now, id)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		rowsAffected, _ := res.RowsAffected()
		if rowsAffected == 0 {
			return c.Status(404).JSON(fiber.Map{"error": "Entry not found"})
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, content, user, summary, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.Content, req.ModifiedBy, req.Summary, now)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		var title string
		db.QueryRow("SELECT title FROM entries WHERE id = ?", id).Scan(&title)

		return c.JSON(Entry{
			ID:             id,
			Title:          title,
			Content:        req.Content,
			LastModifiedBy: req.ModifiedBy,
			LastModifiedAt: now,
		})
	})

	// GET /entries/{entryId}/edits - View history
	app.Get("/entries/:entryId/edits", func(c *fiber.Ctx) error {
		id := c.Params("entryId")
		
		var exists int
		db.QueryRow("SELECT 1 FROM entries WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			return c.Status(404).SendString("Entry not found")
		}

		rows, err := db.Query("SELECT content, user, summary, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", id)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}
		defer rows.Close()

		html := "<h1>Edit History</h1><table border='1'><tr><th>User</th><th>Summary</th><th>Date</th><th>Content Snapshot</th></tr>"
		for rows.Next() {
			var content, user, summary string
			var createdAt time.Time
			rows.Scan(&content, &user, &summary, &createdAt)
			html += fmt.Sprintf("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>", 
				user, summary, createdAt.Format(time.RFC1123), content)
		}
		html += "</table><br><a href='/entries'>Back to List</a>"
		
		c.Set("Content-Type", "text/html")
		return c.SendString(html)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}