package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"strconv"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

type Message struct {
	Content  string `json:"content" binding:"required"`
	Username string `json:"username" binding:"required"`
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
		log.Fatalf("%s", err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	// HTML Template for rendering messages
	tmpl := template.Must(template.New("forum").Parse(`
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
			{{range .}}
				<p><strong>{{.Username}}</strong>: {{.Content}}</p>
			{{else}}
				<p>No messages yet.</p>
			{{end}}
		</body>
		</html>
	`))

	r.SetHTMLTemplate(tmpl)

	r.GET("/messages", func(c *gin.Context) {
		limitStr := c.DefaultQuery("limit", "10")
		offsetStr := c.DefaultQuery("offset", "0")
		sort := c.DefaultQuery("sort", "DESC")

		limit, _ := strconv.Atoi(limitStr)
		offset, _ := strconv.Atoi(offsetStr)

		if sort != "ASC" && sort != "DESC" {
			sort = "DESC"
		}

		query := fmt.Sprintf("SELECT username, content FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", sort)
		rows, err := db.Query(query, limit, offset)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
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

		c.HTML(http.StatusOK, "forum", messages)
	})

	r.POST("/messages", func(c *gin.Context) {
		// Handle both JSON and Form data to make the HTML form work
		var msg Message
		if c.ContentType() == "application/json" {
			if err := c.ShouldBindJSON(&msg); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
				return
			}
		} else {
			msg.Username = c.PostForm("username")
			msg.Content = c.PostForm("content")
			if msg.Username == "" || msg.Content == "" {
				c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
				return
			}
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", msg.Username, msg.Content)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}

		c.Status(http.StatusOK)
	})

	// Use APP_SECRET if provided, though not strictly needed for this basic implementation
	_ = os.Getenv("APP_SECRET")

	r.Run("0.0.0.0:5000")
}