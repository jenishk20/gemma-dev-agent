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
	ID        int
	UserID    string
	Summary   string
	Content   string
	CreatedAt time.Time
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
		user_id TEXT,
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
	mux.HandleFunc("/entries/", entryDetailHandler)

	log.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}

func entriesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		rows, err := db.Query("SELECT id, title FROM entries")
		if err != nil {
			http.Error(w, err.Error(), 500)
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
		sb.WriteString("</ul><hr><p>To create a new entry, send a POST request with JSON.</p>")
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(sb.String()))
		return
	}

	if r.Method == http.MethodPost {
		var ne NewEntry
		if err := json.NewDecoder(r.Body).Decode(&ne); err != nil {
			http.Error(w, "Invalid JSON", 400)
			return
		}

		id := uuid.New().String()
		now := time.Now()
		_, err := db.Exec("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.Title, ne.Content, ne.CreatedBy, now)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, user_id, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.CreatedBy, "Initial creation", ne.Content, now)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}

		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(Entry{ID: id, Title: ne.Title, Content: ne.Content, LastModifiedBy: ne.CreatedBy, LastModifiedAt: now})
		return
	}

	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func entryDetailHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/entries/")
	if strings.Contains(path, "/edits") {
		handleEdits(w, r, strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/entries/"), "/edits"))
		return
	}

	entryId := path
	if r.Method == http.MethodGet {
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", entryId).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		if err == sql.ErrNoRows {
			http.Error(w, "Entry not found", 404)
			return
		} else if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}

		tmpl := `<h1>{{.Title}}</h1>
		<p><b>Content:</b><br>{{.Content}}</p>
		<p><i>Last modified by {{.LastModifiedBy}} on {{.LastModifiedAt}}</i></p>
		<a href="/entries">Back to list</a> | <a href="/entries/{{.ID}}/edits">View History</a>`
		t := template.Must(template.New("entry").Parse(tmpl))
		w.Header().Set("Content-Type", "text/html")
		t.Execute(w, e)
		return
	}

	if r.Method == http.MethodPut {
		var ue UpdateEntry
		if err := json.NewDecoder(r.Body).Decode(&ue); err != nil {
			http.Error(w, "Invalid JSON", 400)
			return
		}

		now := time.Now()
		res, err := db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			ue.Content, ue.ModifiedBy, now, entryId)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		rows, _ := res.RowsAffected()
		if rows == 0 {
			http.Error(w, "Entry not found", 404)
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, user_id, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			entryId, ue.ModifiedBy, ue.Summary, ue.Content, now)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}

		var e Entry
		db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", entryId).
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

	rows, err := db.Query("SELECT id, user_id, summary, content, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", entryId)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	defer rows.Close()

	var edits []EditHistory
	for rows.Next() {
		var eh EditHistory
		rows.Scan(&eh.ID, &eh.UserID, &eh.Summary, &eh.Content, &eh.CreatedAt)
		edits = append(edits, eh)
	}

	if len(edits) == 0 {
		// Check if entry exists at all
		var exists int
		db.QueryRow("SELECT 1 FROM entries WHERE id = ?", entryId).Scan(&exists)
		if exists == 0 {
			http.Error(w, "Entry not found", 404)
			return
		}
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("<h1>Edit History for %s</h1><ul>", entryId))
	for i, edit := range edits {
		diff := "Initial version"
		if i < len(edits)-1 {
			diff = fmt.Sprintf("Changed from: %s", edits[i+1].Content)
		}
		sb.WriteString(fmt.Sprintf("<li><b>%s</b>: %s <br><i>%s</i><br>Content: %s</li><br>",
			edit.CreatedAt.Format(time.RFC1123), edit.UserID, edit.Summary, edit.Content))
		sb.WriteString(fmt.Sprintf("<p>Diff: %s</p>", diff))
		sb.WriteString("</ul>")
	}
	sb.WriteString("<br><a href='/entries'>Back to list</a>")
	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(sb.String()))
}