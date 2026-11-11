package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html"
	"log"
	"net/http"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/google/uuid"
)

// Models
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
	Timestamp   time.Time
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
		timestamp DATETIME,
		FOREIGN KEY(entry_id) REFERENCES entries(id)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func handleEntries(w http.ResponseWriter, r *http.Request) {
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
			sb.WriteString(fmt.Sprintf("<li><a href='/entries/%s'>%s</a></li>", id, html.EscapeString(title)))
		}
		sb.WriteString("</ul><hr><p>Create New: <a href='/create'>New Entry Form</a></p>")
		w.Header().Set("Content-Type", "text/html")
		fmt.Fprint(w, sb.String())
		return
	}

	if r.Method == http.MethodPost {
		var ne NewEntry
		if err := json.NewDecoder(r.Body).Decode(&ne); err != nil {
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}

		id := uuid.New().String()
		now := time.Now()
		_, err := db.Exec("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.Title, ne.Content, ne.CreatedBy, now)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, timestamp) VALUES (?, ?, ?, ?, ?)",
			id, ne.CreatedBy, "Initial creation", ne.Content, now)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(Entry{ID: id, Title: ne.Title, Content: ne.Content, LastModifiedBy: ne.CreatedBy, LastModifiedAt: now})
		return
	}
	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func handleEntryDetail(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/entries/")
	if strings.Contains(id, "/") {
		// This handles the /entries/{id}/edits route
		parts := strings.Split(id, "/")
		if parts[1] == "edits" {
			handleEdits(w, r, parts[0])
			return
		}
	}

	if r.Method == http.MethodGet {
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		if err == sql.ErrNoRows {
			http.Error(w, "Entry not found", http.StatusNotFound)
			return
		}

		var contributors string
		err = db.QueryRow("SELECT group_concat(DISTINCT contributor) FROM edits WHERE entry_id = ?", id).Scan(&contributors)
		if err != nil {
			contributors = "Unknown"
		}

		w.Header().Set("Content-Type", "text/html")
		fmt.Fprintf(w, "<h1>%s</h1><p>Last modified by %s at %s</p><div>%s</div><hr><p>Contributors: %s</p><br><a href='/entries/%s/edits'>View History</a><br><br><a href='/entries'>Back to List</a>",
			html.EscapeString(e.Title), html.EscapeString(e.LastModifiedBy), e.LastModifiedAt.Format(time.RFC1123), 
			html.EscapeString(e.Content), html.EscapeString(contributors), e.ID)
		return
	}

	if r.Method == http.MethodPut {
		var ue UpdateEntry
		if err := json.NewDecoder(r.Body).Decode(&ue); err != nil {
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}

		now := time.Now()
		res, err := db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			ue.Content, ue.ModifiedBy, now, id)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		count, _ := res.RowsAffected()
		if count == 0 {
			http.Error(w, "Entry not found", http.StatusNotFound)
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, timestamp) VALUES (?, ?, ?, ?, ?)",
			id, ue.ModifiedBy, ue.Summary, ue.Content, now)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		var e Entry
		db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(e)
		return
	}
	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func handleEdits(w http.ResponseWriter, r *http.Request, entryId string) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	rows, err := db.Query("SELECT contributor, summary, content, timestamp FROM edits WHERE entry_id = ? ORDER BY timestamp DESC", entryId)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("<h1>Edit History for %s</h1><ul>", html.EscapeString(entryId)))
	
	hasRows := false
	for rows.Next() {
		hasRows = true
		var h EditHistory
		rows.Scan(&h.Contributor, &h.Summary, &h.Content, &h.Timestamp)
		sb.WriteString(fmt.Sprintf("<li><strong>%s</strong> (%s) - %s<br><pre>%s</pre></li><hr>", 
			html.EscapeString(h.Contributor), h.Timestamp.Format(time.RFC1123), html.EscapeString(h.Summary), html.EscapeString(h.Content)))
	}
	
	if !hasRows {
		// Check if entry exists at all
		var exists int
		db.QueryRow("SELECT 1 FROM entries WHERE id = ?", entryId).Scan(&exists)
		if exists == 0 {
			http.Error(w, "Entry not found", http.StatusNotFound)
			return
		}
	}

	sb.WriteString("</ul><a href='/entries'>Back to List</a>")
	w.Header().Set("Content-Type", "text/html")
	fmt.Fprint(w, sb.String())
}

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/entries", handleEntries)
	mux.HandleFunc("/entries/", handleEntryDetail)

	log.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", mux); err != nil {
		log.Fatal(err)
	}
}