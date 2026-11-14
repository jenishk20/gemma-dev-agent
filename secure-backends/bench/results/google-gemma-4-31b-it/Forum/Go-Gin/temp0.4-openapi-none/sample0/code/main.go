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
	ID       int    `json:"id"`
	Username string `json:"username"`
	Content  string `json:"content"`
	Created  string `json:"created"`
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

	r := gin.Default()

	// HTML Template for the forum view
	tmpl := template.New("forum").Funcs(template.FuncMap{
		"escape": func(s string) string {
			return template.HTMLEscapeString(s)
		},
	})

	// Simple HTML layout embedded in the code
	const htmlTemplate = `
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
		<div id="messages">
			{{range .}}
				<p><strong>{{.Username}}</strong>: {{.Content}} <small>({{.Created}})</small></p>
			{{end}}
		</div>
	</body>
	</html>`

	tmpl, err := tmpl.Parse(htmlTemplate)
	if err != nil {
		log.Fatal(err)
	}

	r.GET("/messages", func(c *gin.Context) {
		limitStr := c.DefaultQuery("limit", "10")
		offsetStr := c.DefaultQuery("offset", "0")
		sort := c.DefaultQuery("sort", "DESC")

		limit, _ := strconv.Atoi(limitStr)
		offset, _ := strconv.Atoi(offsetStr)

		if sort != "ASC" && sort != "DESC" {
			sort = "DESC"
		}

		query := fmt.Sprintf("SELECT id, username, content, created_at FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", sort)
		rows, err := db.Query(query, limit, offset)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}
		defer rows.Close()

		var messages []Message
		for rows.Next() {
			var m Message
			if err := rows.Scan(&m.ID, &m.Username, &m.Content, &m.Created); err != nil {
				continue
			}
			messages = append(messages, m)
		}

		c.Header("Content-Type", "text/html")
		r.cCtxt = c // Hack to pass context if needed, but we use tmpl
		c.Writer.WriteHeader(http.StatusOK)
		tmpl.Execute(c.Writer, messages)
	})

	r.POST("/messages", func(c *gin.Context) {
		// The OpenAPI spec says requestBody is application/json
		var msg Message
		if err := c.ShouldBindJSON(&msg); err != nil {
			// Fallback to form data if JSON fails, to make the HTML form work
			msg.Username = c.PostForm("username")
			msg.Content = c.PostForm("content")
			if msg.Username == "" || msg.Content == "" {
				c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
				return
			}
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", msg.Username, msg.Content)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.Status(http.StatusOK)
	})

	// Use APP_SECRET if provided (though not required for basic functionality)
	_ = os.Getenv("APP_SECRET")

	r.Run("0.0.0.0:5000")
}

// Helper to avoid unused variable in Gin context if needed
type contextWrapper struct {
	gin.Context
}
var r_ctx *contextWrapper