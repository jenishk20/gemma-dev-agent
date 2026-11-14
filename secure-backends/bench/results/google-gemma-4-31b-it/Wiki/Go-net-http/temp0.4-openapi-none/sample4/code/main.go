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

type Edit struct {
	ID         int
	Contributor string
	Summary    string
	Content    string
	CreatedAt  time.Time
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
	mux.HandleFunc("/entries", handleEntries)
	mux.HandleFunc("/entries/", handleEntryDetail)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
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
		sb.WriteString("</ul><hr><p>To create a new entry, send a POST request with JSON.</p>")
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(sb.String()))

	} else if r.Method == http.MethodPost {
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

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			id, ne.CreatedBy, "Initial creation", ne.Content, now)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(Entry{ID: id, Title: ne.Title, Content: ne.Content, LastModifiedBy: ne.CreatedBy, LastModifiedAt: now})
	} else {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func handleEntryDetail(w http.ResponseWriter, r *http.Request) {
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(pathParts) < 2 {
		http.NotFound(w, r)
		return
	}
	entryId := pathParts[1]

	if len(pathParts) == 3 && pathParts[2] == "edits" {
		handleEdits(w, r, entryId)
		return
	}

	if r.Method == http.MethodGet {
		var e Entry
		err := db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", entryId).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		if err == sql.ErrNoRows {
			http.NotFound(w, r)
			return
		} else if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		var contributors []string
		rows, _ := db.Query("SELECT DISTINCT contributor FROM edits WHERE entry_id = ?", entryId)
		for rows.Next() {
			var c string
			rows.Scan(&c)
			contributors = append(contributors, c)
		}
		rows.Close()

		w.Header().Set("Content-Type", "text/html")
		fmt.Fprintf(w, "<h1>%s</h1><p>%s</p><hr><p>Last modified by %s at %s</p><p>Contributors: %s</p><a href='/entries/%s/edits'>View History</a>",
			html.EscapeString(e.Title), html.EscapeString(e.Content), html.EscapeString(e.LastModifiedBy), e.LastModifiedAt.Format(time.RFC1123),
			strings.Join(contributors, ", "), e.ID)

	} else if r.Method == http.MethodPut {
		var ue UpdateEntry
		if err := json.NewDecoder(r.Body).Decode(&ue); err != nil {
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}

		now := time.Now()
		res, err := db.Exec("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
			ue.Content, ue.ModifiedBy, now, entryId)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		count, _ := res.RowsAffected()
		if count == 0 {
			http.NotFound(w, r)
			return
		}

		_, err = db.Exec("INSERT INTO edits (entry_id, contributor, summary, content, created_at) VALUES (?, ?, ?, ?, ?)",
			entryId, ue.ModifiedBy, ue.Summary, ue.Content, now)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		var e Entry
		db.QueryRow("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", entryId).
			Scan(&e.ID, &e.Title, &e.Content, &e.LastModifiedBy, &e.LastModifiedAt)
		json.NewEncoder(w).Encode(e)
	} else {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func handleEdits(w http.ResponseWriter, r *http.Request, entryId string) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var exists bool
	err := db.QueryRow("SELECT EXISTS(SELECT 1 FROM entries WHERE id = ?)", entryId).Scan(&exists)
	if err != nil || !exists {
		http.NotFound(w, r)
		return
	}

	rows, err := db.Query("SELECT contributor, summary, content, created_at FROM edits WHERE entry_id = ? ORDER BY created_at DESC", entryId)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	w.Header().Set("Content-Type", "text/html")
	fmt.Fprintf(w, "<h1>Edit History</h1><ul>")
	for rows.Next() {
		var ed Edit
		rows.Scan(&ed.Contributor, &ed.Summary, &ed.Content, &ed.CreatedAt)
		fmt.Fprintf(w, "<li><strong>%s</strong> (%s) - %s: <i>%s</i></li>",
			html.EscapeString(ed.Contributor), ed.CreatedAt.Format(time.RFC1123), html.EscapeString(ed.Summary), html.EscapeString(ed.Content))
	}
	fmt.Fprintf(w, "</ul><a href='/entries/%s'>Back to entry</a>", entryId)
}