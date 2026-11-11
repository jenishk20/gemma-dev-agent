package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/google/uuid"
)

// Models based on OpenAPI schema
type Entry struct {
	ID             string    `json:"id"`
	Title          string    `json:"title"`
	Content        string    `json:"content"`
	LastModifiedBy string    `json:"lastModifiedBy"`
	LastModifiedAt time.Time `json:"lastModifiedAt"`
}

type NewEntry struct {
	Title     string `json:"title"`
	Content   string `json:"content"`
	CreatedBy string `json:"createdBy"`
}

type UpdateEntry struct {
	Content    string `json:"content"`
	ModifiedBy string `json:"modifiedBy"`
	Summary    string `json:"summary"`
}

type EditHistory struct {
	ID          int
	Contributor string
	Summary     string
	Content     string
	CreatedAt   time.Time
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS entries (
		id TEXT PRIMARY KEY,
		title TEXT,
		content TEXT,
		last_modified_by TEXT,
		last_modified_at DATETIME
	);
	CREATE TABLE IF NOT EXISTS edits (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		entry_id TEXT,
		contributor TEXT,
		summary TEXT,
		content TEXT,
		created_at DATETIME,
		FOREIGN KEY(entry_id) REFERENCES entries(id)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("/entries", entriesHandler)
	mux.HandleFunc("/entries/", entryHandler) // Handles /entries/{id} and /entries/{id}/edits

	fmt.Println("Server starting on 0.0.0.0:5000")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}

func entriesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		rows, err := db.Query("SELECT id, title FROM entries")
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var sb strings.Builder
		sb.WriteString("<h1>Wiki Entries</h1><ul>")
		for rows.Next() {
			var id, title string
			rows.Scan(&id, &title)
			sb.WriteString(fmt.Sprintf("<li><a href='/entries/%s'>%s</a></li>", id, title))
		}
		sb.WriteString("</ul><hr><form method='POST' action='/entries'>")
		sb.WriteString("<h3>Create New Entry</h3>")
		sb.WriteString("Title: <input name='title'><br>Content: <textarea name='content'></textarea><br>Author: <input name='author'><br><input type='submit' value='Create'></form>")

		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(sb.String()))
		return
	}

	if r.Method == http.MethodPost {
		// Support both JSON and Form for convenience in the HTML UI
		var ne NewEntry
		if strings.Contains(r.Header.Get("Content-Type"), "application/json") {
			if err := json.NewDecoder(r.Body).Decode(&ne); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
		} else {
			ne.Title = r.FormValue("title")
			ne.Content = r.FormValue("content")
			ne.CreatedBy = r.FormValue("author")
		}

		id := uuid.New().String()
		now := time.Now()
		_, err := db.Exec("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.Title, ne.Content, ne.CreatedBy, now)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.CreatedBy, "Initial creation", ne.Content, now)

		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(Entry{ID: id, Title: ne.Title, Content: ne.Content, LastModifiedBy: ne.CreatedBy, LastModifiedAt: now})
		return
	}
}

func entryHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/entries/")
	parts := strings.Split(path, "/")
	entryId := parts[0]

	if len(parts) > 1 && parts[1] == "edits" {
		handleEdits(w, r, entryId)
		return
	}

	if r.Method == http.MethodGet {
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", entryId).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		if err == sql.ErrNoRows {
			http.Error(w, "Entry not found", http.StatusNotFound)
			return
		}

		var sb strings.Builder
		sb.WriteString(fmt.Sprintf("<h1>%s</h1>", e.Title))
		sb.WriteString(fmt.Sprintf("<p>Last modified by %s at %s</p>", e.LastModifiedBy, e.LastModifiedAt.Format(time.RFC1123)))
		sb.WriteString(fmt.Sprintf("<div>%s</div>", e.Content))
		sb.WriteString(fmt.Sprintf("<hr><a href='/entries/%s/edits'>View History</a> | <a href='/entries'>Back to List</a>", entryId))
		sb.WriteString(fmt.Sprintf("<hr><form method='POST' action='/entries/%s'>", entryId))
		sb.WriteString("<input type='hidden' name='_method' value='PUT'>")
		sb.WriteString("<h3>Edit Entry</h3>Content: <textarea name='content'>"+e.Content+"</textarea><br>Your Name: <input name='author'><br>Summary: <input name='summary'><br><input type='submit' value='Update'></form>")

		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(sb.String()))
		return
	}

	// Handle PUT (via hidden field for HTML forms or actual PUT)
	if r.Method == http.MethodPut || (r.Method == http.MethodPost && r.FormValue("_method") == "PUT") {
		var ue UpdateEntry
		if strings.Contains(r.Header.Get("Content-Type"), "application/json") {
			if err := json.NewDecoder(r.Body).Decode(&ue); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
		} else {
			ue.Content = r.FormValue("content")
			ue.ModifiedBy = r.FormValue("author")
			ue.Summary = r.FormValue("summary")
		}

		now := time.Now()
		res, err := db.Exec("UPDATE entries SET content=?, last_modified_by=?, last_modified_at=? WHERE id=?",
			ue.Content, ue.ModifiedBy, now, entryId)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		count, _ := res.RowsAffected()
		if count == 0 {
			http.Error(w, "Entry not found", http.StatusNotFound)
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			entryId, ue.ModifiedBy, ue.Summary, ue.Content, now)

		var updated Entry
		err = db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", entryId).
			Scan(&updated.ID, &updated.Title, &updated.Content, &updated.LastModifiedBy, &updated.LastModifiedAt)

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(updated)
		return
	}
}

func handleEdits(w http.ResponseWriter, r *http.Request, entryId string) {
	rows, err := db.Query("SELECT contributor, summary, content, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", entryId)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("<h1>Edit History for %s</h1>", entryId))
	sb.WriteString("<ul>")
	hasRows := false
	for rows.Next() {
		hasRows = true
		var h EditHistory
		rows.Scan(&h.Contributor, &h.Summary, &h.Content, &h.CreatedAt)
		sb.WriteString(fmt.Sprintf("<li><strong>%s</strong> (%s) - %s<br><pre>%s</pre></li>",
			h.Contributor, h.CreatedAt.Format(time.RFC1123), h.Summary, h.Content))
	}
	sb.WriteString("</ul><a href='/entries'>Back to List</a>")

	if !hasRows {
		// Check if entry exists at all
		var exists int
		db.QueryRow("SELECT 1 FROM entries WHERE id = ?", entryId).Scan(&exists)
		if exists == 0 {
			http.Error(w, "Entry not found", http.StatusNotFound)
			return
		}
	}

	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(sb.String()))
}

func init() {
	// This is just to satisfy the compiler for the template package if used, 
	// though we used strings.Builder for simplicity.
	_ = template.New("wiki")
}