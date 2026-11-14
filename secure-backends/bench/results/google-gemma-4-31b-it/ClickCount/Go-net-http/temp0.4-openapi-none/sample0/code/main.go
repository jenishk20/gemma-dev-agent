package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/google/uuid"
)

type Click struct {
	ID        string    `json:"id"`
	Timestamp time.Time `json:"timestamp"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS clicks (
		id TEXT PRIMARY KEY,
		timestamp DATETIME
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func handleRegisterClick(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id := uuid.New().String()
	timestamp := time.Now().UTC()

	_, err := db.Exec("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", id, timestamp)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func handleRetrieveClicks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	dateStr := r.URL.Query().Get("date")
	direction := r.URL.Query().Get("direction")

	if dateStr == "" || direction == "" {
		http.Error(w, "Missing required parameters: date and direction", http.StatusBadRequest)
		return
	}

	// Validate direction enum
	validDirections := map[string]bool{"<": true, ">": true, "<=": true, ">=": true}
	if !validDirections[direction] {
		http.Error(w, "Invalid direction. Must be <, >, <=, or >=", http.StatusBadRequest)
		return
	}

	// Validate date format (YYYY-MM-DD)
	_, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		http.Error(w, "Invalid date format. Use YYYY-MM-DD", http.StatusBadRequest)
		return
	}

	// We use a parameterized query for the date, but the operator must be hard-coded/validated
	// since SQL drivers don't allow parameterizing operators.
	query := fmt.Sprintf("SELECT id, timestamp FROM clicks WHERE timestamp %s ?", direction)
	rows, err := db.Query(query, dateStr)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var clicks []Click
	for rows.Next() {
		var c Click
		if err := rows.Scan(&c.ID, &c.Timestamp); err != nil {
			http.Error(w, "Error scanning results", http.StatusInternalServerError)
			return
		}
		clicks = append(clicks, c)
	}

	if len(clicks) == 0 {
		http.Error(w, "No clicks found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(clicks)
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/click", handleRegisterClick)
	http.HandleFunc("/clicks", handleRetrieveClicks)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}