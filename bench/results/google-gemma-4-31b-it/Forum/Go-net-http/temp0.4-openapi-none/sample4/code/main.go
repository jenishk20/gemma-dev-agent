package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
)

type Message struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Content  string `json:"content"`
}

var db *sql.DB

const htmlTemplate = `
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .username { font-weight: bold; color: #555; }
        .controls { margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    <div class="controls">
        <form action="/messages" method="POST" id="postForm">
            <input type="text" name="username" placeholder="Username" required><br>
            <textarea name="content" placeholder="Message" required></textarea><br>
            <button type="submit">Post Message</button>
        </form>
        <p><small>Note: The API expects JSON for POST, but this form is for convenience. Use a tool like curl for JSON POST.</small></p>
    </div>
    <hr>
    <div id="messages">
        {{range .}}
        <div class="message">
            <span class="username">{{.Username}}</span>: {{.Content}}
        </div>
        {{else}}
        <p>No messages yet.</p>
        {{end}}
    </div>
</body>
</html>
`

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
		log.Fatalf("Database init failed: %q: %s\n", err, sqlStmt)
	}
}

func messagesHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		limitStr := r.URL.Query().Get("limit")
		offsetStr := r.URL.Query().Get("offset")
		sort := r.URL.Query().Get("sort")

		limit := 10
		if l, err := strconv.Atoi(limitStr); err == nil {
			limit = l
		}
		offset := 0
		if o, err := strconv.Atoi(offsetStr); err == nil {
			offset = o
		}

		orderBy := "DESC"
		if sort == "ASC" {
			orderBy = "ASC"
		} else if sort != "DESC" && sort != "desc" {
			orderBy = "DESC"
		} else if sort == "desc" {
			orderBy = "DESC"
		}

		query := fmt.Sprintf("SELECT id, username, content FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", orderBy)
		rows, err := db.Query(query, limit, offset)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var messages []Message
		for rows.Next() {
			var m Message
			if err := rows.Scan(&m.ID, &m.Username, &m.Content); err != nil {
				continue
			}
			messages = append(messages, m)
		}

		tmpl, err := template.New("webpage").Parse(htmlTemplate)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "text/html")
		tmpl.Execute(w, messages)

	case http.MethodPost:
		var m Message
		// Handle both JSON and Form data for usability
		if r.Header.Get("Content-Type") == "application/json" {
			if err := json.NewDecoder(r.Body).Decode(&m); err != nil {
				http.Error(w, "Invalid JSON", http.StatusBadRequest)
				return
			}
		} else {
			if err := r.ParseForm(); err != nil {
				http.Error(w, "Invalid form data", http.StatusBadRequest)
				return
			}
			m.Username = r.FormValue("username")
			m.Content = r.FormValue("content")
		}

		if m.Username == "" || m.Content == "" {
			http.Error(w, "Username and content are required", http.StatusBadRequest)
			return
		}

		_, err := db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", m.Username, m.Content)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/messages", messagesHandler)

	port := "0.0.0.0:5000"
	fmt.Printf("Server starting on %s\n", port)
	log.Fatal(http.ListenAndServe(port, nil))
}