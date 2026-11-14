package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
)

type Message struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Content  string `json:"content"`
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

func messagesHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		handleGetMessages(w, r)
	case http.MethodPost:
		handlePostMessage(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func handleGetMessages(w http.ResponseWriter, r *http.Request) {
	limitStr := r.URL.Query().Get("limit")
	offsetStr := r.URL.Query().Get("offset")
	sortDir := r.URL.Query().Get("sort")

	limit := 10
	if l, err := strconv.Atoi(limitStr); err == nil {
		limit = l
	}

	offset := 0
	if o, err := strconv.Atoi(offsetStr); err == nil {
		offset = o
	}

	if sortDir != "ASC" && sortDir != "DESC" {
		sortDir = "DESC"
	}

	query := fmt.Sprintf("SELECT id, username, content FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", sortDir)
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

	tmpl := `
	<!DOCTYPE html>
	<html>
	<head><title>MyForum</title></head>
	<body>
		<h1>MyForum</h1>
		<form method="POST" action="/messages" style="margin-bottom: 20px;">
			<input type="text" name="username" placeholder="Username" required>
			<input type="text" name="content" placeholder="Message" required>
			<button type="submit">Post</button>
		</form>
		<hr>
		{{range .}}
			<div style="border-bottom: 1px solid #ccc; padding: 10px 0;">
				<strong>{{.Username}}</strong>: {{.Content}}
			</div>
		{{else}}
			<p>No messages yet.</p>
		{{end}}
	</body>
	</html>`

	t, err := template.New("webpage").Parse(tmpl)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html")
	t.Execute(w, messages)
}

func handlePostMessage(w http.ResponseWriter, r *http.Request) {
	var m Message
	err := json.NewDecoder(r.Body).Decode(&m)
	if err != nil || m.Username == "" || m.Content == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	_, err = db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", m.Username, m.Content)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/messages", messagesHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}