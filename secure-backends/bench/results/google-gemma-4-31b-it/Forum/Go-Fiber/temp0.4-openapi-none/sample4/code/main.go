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
	_, err = db.Exec(createTable)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// HTML Template for the forum
	forumTemplate := template.Must(template.New("forum").Parse(`
<!DOCTYPE html>
<html>
<head><title>MyForum</title></head>
<body>
	<h1>MyForum</h1>
	<form action="/messages" method="POST">
		<input type="text" name="username" placeholder="Username" required><br>
		<textarea name="content" placeholder="Message" required></textarea><br>
		<button type="submit">Post</button>
	</form>
	<hr>
	<h2>Messages</h2>
	{{range .Messages}}
		<p><strong>{{.Username}}</strong>: {{.Content}}</p>
	{{else}}
		<p>No messages yet.</p>
	{{end}}
</body>
</html>
`))

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

		c.Set("Content-Type", "text/html")
		return forumTemplate.Execute(c.Response().BodyWriter(), fiber.Map{
			"Messages": messages,
		})
	})

	app.Post("/messages", func(c *fiber.Ctx) error {
		// Support both JSON and Form data for better UX in the browser
		var msg Message
		if c.Is("application/json") {
			if err := c.BodyParser(&msg); err != nil {
				return c.Status(400).SendString("Invalid JSON")
			}
		} else {
			msg.Username = c.FormValue("username")
			msg.Content = c.FormValue("content")
		}

		if msg.Username == "" || msg.Content == "" {
			return c.Status(400).SendString("Username and content are required")
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", msg.Username, msg.Content)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}

		return c.SendStatus(200)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}