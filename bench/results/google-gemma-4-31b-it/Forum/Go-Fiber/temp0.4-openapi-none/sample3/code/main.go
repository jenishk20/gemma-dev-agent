package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"strconv"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/logger"
	_ "github.com/mattn/go-sqlite3"
)

type Message struct {
	Content  string `json:"content"`
	Username string `json:"username"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS messages (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT,
		content TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
	app.Use(logger.New())

	// HTML Template for the forum
	app.Set("forum_template", template.Must(template.New("forum").Parse(`
		<!DOCTYPE html>
		<html>
		<head><title>MyForum</title></head>
		<body>
			<h1>MyForum</h1>
			<form action="/messages" method="POST">
				<input type="text" name="username" placeholder="Username" required><br>
				<textarea name="content" placeholder="Message" required></textarea><br>
				<button type="submit">Post Message</button>
			</form>
			<hr>
			<h2>Messages</h2>
			<ul>
				{{range .}}
				<li><strong>{{.Username}}</strong>: {{.Content}}</li>
				{{end}}
			</ul>
		</body>
		</html>
	`)))

	app.Get("/messages", func(c *fiber.Ctx) error {
		limitStr := c.Query("limit", "10")
		offsetStr := c.Query("offset", "0")
		sort := c.Query("sort", "DESC")

		limit, _ := strconv.Atoi(limitStr)
		offset, _ := strconv.Atoi(offsetStr)

		if sort != "ASC" && sort != "DESC" {
			sort = "DESC"
		}

		query := fmt.Sprintf("SELECT username, content FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", sort)
		rows, err := db.Query(query, limit, offset)
		if err != nil {
			return c.Status(http.StatusInternalServerError).SendString(err.Error())
		}
		defer rows.Close()

		var messages []Message
		for rows.Next() {
			var m Message
			if err := rows.Scan(&m.Username, &m.Content); err != nil {
				continue
			}
			messages = append(messages, m)
		}

		// The OpenAPI spec requires text/html response for GET /messages
		// Since we need to handle the form submission too, we use a simple template
		tmpl := app.Get("forum_template").(*template.Template)
		
		// We use a buffer to render the template to a string for Fiber
		// However, Fiber's Render is usually for specific engines. 
		// We will use a simple custom response for the HTML content.
		
		// To satisfy the "text/html" requirement of the schema:
		c.Set("Content-Type", "text/html")
		
		// We manually render the template to the response body
		// Note: In a real app, we'd use fiber.View, but here we keep it in one file.
		// Using a simple trick to render template to fiber response:
		var buf []byte
		// This is a simplified way to render the template for the response
		// Since we can't easily use a buffer with the standard template without a writer,
		// we'll use a custom function.
		
		// For the sake of the exercise and "one file" constraint:
		// We'll use a basic HTML generation if template logic is too verbose, 
		// but let's stick to a simple loop for the HTML.
		
		html := "<html><head><title>MyForum</title></head><body><h1>MyForum</h1>"
		html += "<form action='/messages' method='POST' enctype='application/x-www-form-urlencoded'>"
		html += "Username: <input name='username'><br>Content: <input name='content'><br><input type='submit'>"
		html += "</form><hr><h2>Messages</h2><ul>"
		for _, m := range messages {
			html += fmt.Sprintf("<li><strong>%s</strong>: %s</li>", m.Username, m.Content)
		}
		html += "</ul></body></html>"
		
		return c.SendString(html)
	})

	app.Post("/messages", func(c *fiber.Ctx) error {
		// The schema says requestBody is application/json, 
		// but for a webapp forum, we often receive form data.
		// We will try to parse JSON first, then fallback to Form.
		var m Message
		if err := c.BodyParser(&m); err != nil {
			return c.Status(http.StatusBadRequest).SendString("Invalid input")
		}

		if m.Username == "" || m.Content == "" {
			return c.Status(http.StatusBadRequest).SendString("Username and Content are required")
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", m.Username, m.Content)
		if err != nil {
			return c.Status(http.StatusInternalServerError).SendString(err.Error())
		}

		return c.SendStatus(http.StatusOK)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}