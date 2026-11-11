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
        body { font-family: sans-serif; margin: 20px; max-width: 800px; }
        .msg { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .user { font-weight: bold; color: #555; }
        .content { margin-top: 5px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    <div id="messages">
        {{range .}}
        <div class="msg">
            <div class="user">{{.Username}}</div>
            <div class="content">{{.Content}}</div>
        </div>
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
		log.Fatal(err)
	}
}

func handleMessages(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		var msg Message
		err := json.NewDecoder(r.Body).Decode(&msg)
		if err != nil || msg.Username == "" || msg.Content == "" {
			http.Error(w, "Invalid input", http.StatusBadRequest)
			return
		}

		_, err = db.Exec("INSERT INTO messages (username, content) VALUES (?, ?)", msg.Username, msg.Content)
		if err != nil {
			http.Error(w, "Database error", http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method == http.MethodGet {
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
		rows, err := db.Query(query, limit, offset)
		if err != nil {
			http.Error(w, "Database error", http.StatusInternalServerError)
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

		tmpl, err := template.New("forum").Parse(htmlTemplate)
		if err != nil {
			http.Error(w, "Template error", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "text/html")
		tmpl.Execute(w, messages)
		return
	}

	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/messages", handleMessages)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}