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

	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
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
	Contributor string
	Summary     string
	Timestamp   time.Time
	Content     string
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

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("/entries", entriesHandler)
	mux.HandleFunc("/entries/", entryDetailHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
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

		var list []string
		for rows.Next() {
			var id, title string
			rows.Scan(&id, &title)
			list = append(list, fmt.Sprintf("<li><a href='/entries/%s'>%s</a></li>", id, title))
		}

		w.Header().Set("Content-Type", "text/html")
		fmt.Fprintf(w, "<h1>Wiki Entries</h1><ul>%s</ul><hr><p>Create new entry via POST /entries</p>", strings.Join(list, ""))
		return
	}

	if r.Method == http.MethodPost {
		var ne NewEntry
		if err := json.NewDecoder(r.Body).Decode(&ne); err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
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

func entryDetailHandler(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/entries/")
	if id == "" {
		http.Error(w, "Entry ID required", http.StatusBadRequest)
		return
	}

	// Handle /entries/{id}/edits
	if strings.HasSuffix(id, "/edits") {
		entryId := strings.TrimSuffix(id, "/edits")
		handleEdits(w, entryId)
		return
	}

	if r.Method == http.MethodGet {
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", id).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		if err == sql.ErrNoRows {
			http.Error(w, "Entry not found", http.StatusNotFound)
			return
		} else if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "text/html")
		tmpl := `<h1>{{.Title}}</h1><p>Last edited by {{.LastModifiedBy}} at {{.LastModifiedAt}}</p>
		<div style="border:1px solid #ccc; padding:10px; white-space:pre-wrap;">{{.Content}}</div>
		<hr><a href="/entries">Back to list</a> | <a href="/entries/{{.ID}}/edits">View History</a>`
		t := template.Must(template.New("entry").Parse(tmpl))
		t.Execute(w, e)
		return
	}

	if r.Method == http.MethodPut {
		var ue UpdateEntry
		if err := json.NewDecoder(r.Body).Decode(&ue); err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
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

func handleEdits(w http.ResponseWriter, entryId string) {
	var exists bool
	err := db.QueryRow("SELECT EXISTS(SELECT 1 FROM entries WHERE id = ?)", entryId).Scan(&exists)
	if err != nil || !exists {
		http.Error(w, "Entry not found", http.StatusNotFound)
		return
	}

	rows, err := db.Query("SELECT contributor, summary, timestamp, content FROM edits WHERE entry_id = ? ORDER BY timestamp DESC", entryId)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	w.Header().Set("Content-Type", "text/html")
	fmt.Fprintf(w, "<h1>Edit History for %s</h1>", entryId)
	
	var prevContent string
	for rows.Next() {
		var eh EditHistory
		rows.Scan(&eh.Contributor, &eh.Summary, &eh.Timestamp, &eh.Content)
		
		diff := "Initial Version"
		if prevContent != "" {
			diff = fmt.Sprintf("Changed from: %s -> To: %s", prevContent, eh.Content)
		}
		
		fmt.Fprintf(w, "<div><strong>%s</strong> (%s): %s<br><em>%s</em><hr></div>", 
			eh.Contributor, eh.Timestamp.Format(time.RFC1123), eh.Summary, diff)
		prevContent = eh.Content
	}
	fmt.Fprintf(w, "<a href='/entries/%s'>Back to entry</a>", entryId)
}