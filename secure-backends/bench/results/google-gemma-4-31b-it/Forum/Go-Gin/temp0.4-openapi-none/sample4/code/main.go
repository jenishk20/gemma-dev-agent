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

	// HTML template for the forum view
	tmpl := template.Must(template.New("forum").Parse(`
	<!DOCTYPE html>
	<html>
	<head><title>MyForum</title></head>
	<body>
		<h1>MyForum</h1>
		<form action="/messages" method="POST" style="margin-bottom: 20px;">
			<input type="text" name="username" placeholder="Username" required><br>
			<textarea name="content" placeholder="Message" required></textarea><br>
			<button type="submit">Post</button>
		</form>
		<hr>
		<div id="messages">
			{{range .}}
				<div style="border-bottom: 1px solid #ccc; margin-bottom: 10px;">
					<strong>{{.Username}}</strong> <small>{{.Created}}</small><br>
					{{.Content}}
				</div>
			{{else}}
				<p>No messages yet.</p>
			{{end}}
		</div>
	</body>
	</html>
	`))

	r.GET("/messages", func(c *gin.Context) {
		limitStr := c.DefaultQuery("limit", "10")
		offsetStr := c.DefaultQuery("offset", "0")
		sort := c.DefaultQuery("sort", "DESC")

		limit, errL := strconv.Atoi(limitStr)
		offset, errO := strconv.Atoi(offsetStr)
		if errL != nil || errO != nil {
			c.String(http.StatusBadRequest, "Invalid limit or offset")
			return
		}

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
		tmpl.Execute(c.Writer, messages)
	})

	r.POST("/messages", func(c *gin.Context) {
		var msg Message
		// Support both JSON (per OpenAPI) and Form (for the HTML page)
		if c.ContentType() == "application/json" {
			if err := c.ShouldBindJSON(&msg); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
				return
			}
		} else {
			msg.Username = c.PostForm("username")
			msg.Content = c.PostForm("content")
			if msg.Username == "" || msg.Content == "" {
				c.String(http.StatusBadRequest, "Username and content are required")
				return
			}
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", msg.Username, msg.Content)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}

		if c.ContentType() == "application/json" {
			c.Status(http.StatusOK)
		} else {
			c.Redirect(http.StatusSeeOther, "/messages")
		}
	})

	// Use APP_SECRET if provided (though not strictly needed for this basic logic)
	_ = os.Getenv("APP_SECRET")

	r.Run("0.0.0.0:5000")
}