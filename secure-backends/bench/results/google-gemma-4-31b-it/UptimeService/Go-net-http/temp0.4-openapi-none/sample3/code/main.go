package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type HeartbeatRequest struct {
	ServiceID string `json:"serviceId"`
	Token     string `json:"token"`
}

type TokenRequest struct {
	Token string `json:"token"`
}

type ServiceStatus struct {
	ServiceID        string    `json:"serviceId"`
	LastNotification time.Time `json:"lastNotification"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS services (
		service_id TEXT PRIMARY KEY,
		token TEXT,
		last_notification DATETIME
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func heartbeatHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req HeartbeatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request payload", http.StatusBadRequest)
		return
	}

	if req.ServiceID == "" || req.Token == "" {
		http.Error(w, "serviceId and token are required", http.StatusBadRequest)
		return
	}

	now := time.Now().UTC()
	_, err := db.Exec(`
		INSERT INTO services (service_id, token, last_notification) 
		VALUES (?, ?, ?) 
		ON CONFLICT(service_id) DO UPDATE SET 
		token = excluded.token, 
		last_notification = excluded.last_notification`,
		req.ServiceID, req.Token, now)

	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func servicesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req TokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request payload", http.StatusBadRequest)
		return
	}

	if req.Token == "" {
		http.Error(w, "token is required", http.StatusBadRequest)
		return
	}

	rows, err := db.Query("SELECT service_id, last_notification FROM services WHERE token = ?", req.Token)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var services []ServiceStatus
	for rows.Next() {
		var s ServiceStatus
		if err := rows.Scan(&s.ServiceID, &s.LastNotification); err != nil {
			http.Error(w, "Internal server error", http.StatusInternalServerError)
			return
		}
		services = append(services, s)
	}

	if services == nil {
		services = []ServiceStatus{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(services)
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/heartbeat", heartbeatHandler)
	http.HandleFunc("/services", servicesHandler)

	fmt.Println("Server starting on 0.0.0.0:5000")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}