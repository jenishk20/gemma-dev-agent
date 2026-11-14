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
		content_snapshot TEXT,
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
			if err := rows.Scan(&id, &title); err != nil {
				continue
			}
			html += fmt.Sprintf("<li><a href='/entries/%s'>%s</a></li>", id, title)
		}
		html += "</ul><hr><p>Create new entry via POST /entries</p>"
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

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content_snapshot, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.CreatedBy, "Initial creation", req.Content, now)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

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

		rows, err := db.Query("SELECT contributor FROM edits WHERE entry_id = ?", id)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}
		defer rows.Close()

		contributors := "Contributors: "
		seen := make(map[string]bool)
		for rows.Next() {
			var name string
			rows.Scan(&name)
			if !seen[name] {
				contributors += name + ", "
				seen[name] = true
			}
		}

		html := fmt.Sprintf("<h1>%s</h1><p>Last modified by %s at %s</p><div>%s</div><hr><p>%s</p>",
			e.Title, e.LastModifiedBy, e.LastModifiedAt.Format(time.RFC1123), e.Content, contributors)
		html += fmt.Sprintf("<br><a href='/entries/%s/edits'>View History</a> | <a href='/entries'>Back to List</a>", id)

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
		} else if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		now := time.Now()
		_, err = db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			req.Content, req.ModifiedBy, now, id)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content_snapshot, created_at) VALUES (?, ?, ?, ?, ?)",
			id, req.ModifiedBy, req.Summary, req.Content, now)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

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
		
		var exists int
		db.QueryRow("SELECT 1 FROM entries WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			return c.Status(404).SendString("Entry not found")
		}

		rows, err := db.Query("SELECT contributor, summary, content_snapshot, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", id)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}
		defer rows.Close()

		html := fmt.Sprintf("<h1>Edit History for %s</h1>", id)
		for rows.Next() {
			var contributor, summary, content string
			var createdAt time.Time
			rows.Scan(&contributor, &summary, &content, &createdAt)
			html += fmt.Sprintf("<div><strong>%s</strong> (%s) - %s<br><pre>%s</pre><hr></div>",
				contributor, createdAt.Format(time.RFC1123), summary, content)
		}
		html += "<a href='/entries/"+id+"'>Back to Entry</a>"

		c.Set("Content-Type", "text/html")
		return c.SendString(html)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}