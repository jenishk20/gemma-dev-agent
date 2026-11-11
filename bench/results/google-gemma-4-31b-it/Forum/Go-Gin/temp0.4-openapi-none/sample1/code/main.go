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

type ForumApp struct {
	db *sql.DB
}

func main() {
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Initialize table
	statement := `CREATE TABLE IF NOT EXISTS messages (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT,
		content TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}

	app := &ForumApp{db: db}
	r := gin.Default()

	// HTML Template for rendering messages
	r.SetHTMLTemplate(template.New("forum").Parse(`
<!DOCTYPE html>
<html>
<head><title>MyForum</title></head>
<body>
	<h1>MyForum</h1>
	<form action="/messages" method="POST" enctype="application/json">
		<input type="text" name="username" placeholder="Username" required>
		<input type="text" name="content" placeholder="Message" required>
		<button type="submit">Post</button>
	</form>
	<hr>
	<div id="messages">
		{{range .}}
			<p><strong>{{.Username}}</strong>: {{.Content}}</p>
		{{else}}
			<p>No messages yet.</p>
		{{end}}
	</div>
</body>
</html>
`))

	// Note: The OpenAPI spec asks for POST as application/json. 
	// To support both the JSON API and a basic HTML form for a "webapp" feel, 
	// we handle the POST endpoint.
	r.GET("/messages", app.getMessages)
	r.POST("/messages", app.postMessage)

	// Start server on 0.0.0.0:5000
	r.Run("0.0.0.0:5000")
}

func (app *ForumApp) getMessages(c *gin.Context) {
	limitStr := c.DefaultQuery("limit", "10")
	offsetStr := c.DefaultQuery("offset", "0")
	sort := c.DefaultQuery("sort", "DESC")

	limit, _ := strconv.Atoi(limitStr)
	offset, _ := strconv.Atoi(offsetStr)

	// Validate sort enum
	if sort != "ASC" && sort != "DESC" {
		sort = "DESC"
	}

	query := fmt.Sprintf("SELECT username, content FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", sort)
	rows, err := app.db.Query(query, limit, offset)
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

	// The OpenAPI spec says response content is text/html
	c.HTML(http.StatusOK, "forum", messages)
}

func (app *ForumApp) postMessage(c *gin.Context) {
	var msg Message
	if err := c.ShouldBindJSON(&msg); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
		return
	}

	_, err := app.db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", msg.Username, msg.Content)
	if err != nil {
		c.String(http.StatusInternalServerError, "Database error")
		return
	}

	c.Status(http.StatusOK)
}