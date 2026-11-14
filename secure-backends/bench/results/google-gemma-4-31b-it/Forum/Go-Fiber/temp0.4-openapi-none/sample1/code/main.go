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
	_ "github.com/mattn/go-sqlite3"
)

type Message struct {
	Content  string `json:"content"`
	Username string `json:"username"`
}

type MessageRow struct {
	ID       int
	Content  string
	Username string
	Created  string
}

var db *sql.DB

func main() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS messages (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT,
		content TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	)`)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// HTML Template for the forum
	app.Get("/", func(c *fiber.Ctx) error {
		return c.Redirect("/messages")
	})

	app.Get("/messages", func(c *fiber.Ctx) error {
		limitStr := c.Query("limit", "10")
		offsetStr := c.Query("offset", "0")
		sort := c.Query("sort", "DESC")

		limit, _ := strconv.Atoi(limitStr)
		offset, _ := strconv.Atoi(offsetStr)

		if sort != "ASC" && sort != "DESC" {
			sort = "DESC"
		}

		query := fmt.Sprintf("SELECT id, username, content, created_at FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", sort)
		rows, err := db.Query(query, limit, offset)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}
		defer rows.Close()

		var messages []MessageRow
		for rows.Next() {
			var m MessageRow
			if err := rows.Scan(&m.ID, &m.Username, &m.Content, &m.Created); err != nil {
				continue
			}
			messages = append(messages, m)
		}

		tmpl := `
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
			<div style="display:flex; gap: 10px; margin-bottom: 20px;">
				<a href="/messages?sort=DESC">Newest First</a> | 
				<a href="/messages?sort=ASC">Oldest First</a>
			</div>
			{{range .}}
				<div style="border: 1px solid #ccc; margin: 10px 0; padding: 10px;">
					<strong>{{.Username}}</strong> <small>({{.Created}})</small><br>
					{{.Content}}
				</div>
			{{else}}
				<p>No messages yet!</p>
			{{end}}
		</body>
		</html>`

		t := template.Must(template.New("forum").Parse(tmpl))
		c.Set("Content-Type", "text/html")
		return t.Execute(c.Response().BodyWriter(), messages)
	})

	app.Post("/messages", func(c *fiber.Ctx) error {
		// Support both JSON (as per OpenAPI) and Form data (for the HTML page)
		var msg Message
		if c.Is("json") {
			if err := c.BodyParser(&msg); err != nil {
				return c.Status(400).SendString("Invalid JSON")
			}
		} else {
			if err := c.BodyParser(&msg); err != nil {
				return c.Status(400).SendString("Invalid Form Data")
			}
		}

		if msg.Username == "" || msg.Content == "" {
			return c.Status(400).SendString("Username and content are required")
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", msg.Username, msg.Content)
		if err != nil {
			return c.Status(500).SendString(err.Error())
		}

		if c.Is("json") {
			return c.SendStatus(200)
		}
		return c.Redirect("/messages")
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}