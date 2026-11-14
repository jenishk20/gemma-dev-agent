package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"os"
	"strconv"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

type Message struct {
	Content  string `json:"content"`
	Username string `json:"username"`
}

var db *sql.DB

func main() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	createTable := `CREATE TABLE IF NOT EXISTS messages (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT,
		content TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`
	if _, err := db.Exec(createTable); err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// HTML Template for the forum
	app.Set("template", template.Must(template.New("index").Parse(`
<!DOCTYPE html>
<html>
<head><title>MyForum</title></head>
<body>
	<h1>MyForum</h1>
	<form action="/messages" method="POST">
		<input type="text" name="username" placeholder="Username" required>
		<input type="text" name="content" placeholder="Message" required>
		<button type="submit">Post</button>
	</form>
	<hr>
	<ul>
		{{range .}}
		<li><strong>{{.Username}}</strong>: {{.Content}}</li>
		{{end}}
	</ul>
</body>
</html>`)))

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
			return c.Status(500).SendString(err.Error())
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
		// We use a simple template to render the list
		tmpl := app.Locals("template").(*template.Template)
		
		// Fiber's default response is string, we need to write to a buffer or use a helper
		// Since we are limited to standard lib + fiber, we'll use a simple approach:
		// We'll render the template to a string and send it.
		
		// However, for simplicity and to meet the "text/html" requirement:
		// We can use a custom response.
		
		// To avoid complex buffer logic in one file, we'll use a simple HTML string builder
		// or just use the template.
		
		// Fiber doesn't have a built-in template engine in the core package (it's a separate module),
		// but we can use html/template and write to the response body.
		
		c.Set("Content-Type", "text/html")
		
		// We'll use a simple manual HTML construction to ensure it works without extra modules
		html := "<html><head><title>MyForum</title></head><body><h1>MyForum</h1>"
		html += "<form action='/messages' method='POST'><input name='username' placeholder='Username'><input name='content' placeholder='Message'><button type='submit'>Post</button></form><hr><ul>"
		for _, m := range messages {
			html += fmt.Sprintf("<li><strong>%s</strong>: %s</li>", m.Username, m.Content)
		}
		html += "</ul></body></html>"
		
		return c.SendString(html)
	})

	app.Post("/messages", func(c *fiber.Ctx) error {
		var m Message
		// Try to parse JSON as per OpenAPI spec
		if err := c.BodyParser(&m); err != nil {
			// If JSON fails, try form data for the web UI
			m.Username = c.FormValue("username")
			m.Content = c.FormValue("content")
		}

		if m.Username == "" || m.Content == "" {
			return c.Status(400).SendString("Invalid input")
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", m.Username, m.Content)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}

		return c.SendStatus(200)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}