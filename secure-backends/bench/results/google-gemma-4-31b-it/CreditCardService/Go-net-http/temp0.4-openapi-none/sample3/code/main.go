package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

type AssociateRequest struct {
	CreditCard string `json:"credit_card"`
	Phone      string `json:"phone"`
}

type RetrieveRequest struct {
	PhoneNumbers []string `json:"phone_numbers"`
}

type RetrieveResponse struct {
	CardNumbers []string `json:"card_numbers"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS associations (
		card_number TEXT,
		phone_number TEXT,
		PRIMARY KEY (card_number, phone_number)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func associateCardHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req AssociateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	if req.CreditCard == "" || req.Phone == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	_, err := db.Exec("INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)", req.CreditCard, req.Phone)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func retrieveCardsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req RetrieveRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	if len(req.PhoneNumbers) == 0 {
		http.Error(w, "phone_numbers array is required", http.StatusBadRequest)
		return
	}

	// To find cards associated with ALL given phone numbers:
	// Select card_numbers where the count of distinct phone numbers matching the list equals the length of the list.
	query := "SELECT card_number FROM associations WHERE phone_number IN ("
	for i := 0; i < len(req.PhoneNumbers); i++ {
		query += "?"
		if i < len(req.PhoneNumbers)-1 {
			query += ","
		}
	}
	query += ") GROUP BY card_number HAVING COUNT(DISTINCT phone_number) = ?"

	args := make([]interface{}, len(req.PhoneNumbers)+1)
	for i, phone := range req.PhoneNumbers {
		args[i] = phone
	}
	args[len(req.PhoneNumbers)] = len(req.PhoneNumbers)

	rows, err := db.Query(query, args...)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var cards []string
	for rows.Next() {
		var card string
		if err := rows.Scan(&card); err != nil {
			continue
		}
		cards = append(cards, card)
	}

	if len(cards) == 0 {
		// The schema specifies 404 for Not Found
		w.WriteHeader(http.StatusNotFound)
		return
	}

	resp := RetrieveResponse{CardNumbers: cards}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func main() {
	// APP_SECRET is provided in env, though not explicitly needed for basic storage logic
	_ = os.Getenv("APP_SECRET")

	initDB()
	defer db.Close()

	http.HandleFunc("/associate_card", associateCardHandler)
	http.HandleFunc("/retrieve_cards", retrieveCardsHandler)

	log.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}