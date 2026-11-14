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
	Username string `json:"username"`
	Content  string `json:"content"`
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

	// Initialize database table
	statement, _ := db.Prepare("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
	statement.Exec()

	app := &ForumApp{db: db}

	mux := http.NewServeMux()
	mux.HandleFunc("/messages", app.handleMessages)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}

func (app *ForumApp) handleMessages(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		app.getMessages(w, r)
	case http.MethodPost:
		app.postMessage(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (app *ForumApp) getMessages(w http.ResponseWriter, r *http.Request) {
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

	direction := "DESC"
	if sort == "ASC" {
		direction = "ASC"
	}

	query := fmt.Sprintf("SELECT username, content FROM messages ORDER BY created_at %s LIMIT ? OFFSET ?", direction)
	rows, err := app.db.Query(query, limit, offset)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
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

	tmpl := `
	<!DOCTYPE html>
	<html>
	<head><title>MyForum</title></head>
	<body>
		<h1>Forum Messages</h1>
		<form action="/messages" method="POST" enctype="application/json">
			<input type="text" name="username" placeholder="Username" required><br>
			<textarea name="content" placeholder="Message" required></textarea><br>
			<button type="submit">Post</button>
		</form>
		<hr>
		{{range .}}
			<p><strong>{{.Username}}</strong>: {{.Content}}</p>
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

func (app *ForumApp) postMessage(w http.ResponseWriter, r *http.Request) {
	var m Message
	err := json.NewDecoder(r.Body).Decode(&m)
	if err != nil || m.Username == "" || m.Content == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	_, err = app.db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", m.Username, m.Content)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}