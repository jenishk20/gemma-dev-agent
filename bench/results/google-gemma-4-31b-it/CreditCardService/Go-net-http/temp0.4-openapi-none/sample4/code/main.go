package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
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
		credit_card TEXT,
		phone TEXT,
		PRIMARY KEY (credit_card, phone)
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
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	_, err := db.Exec("INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)", req.CreditCard, req.Phone)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
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
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// To find cards associated with ALL given phone numbers:
	// We group by credit_card and filter for those where the count of distinct phones 
	// matching the input list equals the size of the input list.
	query := "SELECT credit_card FROM associations WHERE phone IN ("
	for i := 0; i < len(req.PhoneNumbers); i++ {
		query += "?"
		if i < len(req.PhoneNumbers)-1 {
			query += ","
		}
	}
	query += ") GROUP BY credit_card HAVING COUNT(DISTINCT phone) = ?"

	args := make([]interface{}, len(req.PhoneNumbers)+1)
	for i, phone := range req.PhoneNumbers {
		args[i] = phone
	}
	args[len(req.PhoneNumbers)] = len(req.PhoneNumbers)

	rows, err := db.Query(query, args...)
	if err != nil {
		log.Printf("Query error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var cards []string
	for rows.Next() {
		var card string
		if err := rows.Scan(&card); err != nil {
			http.Error(w, "Internal server error", http.StatusInternalServerError)
			return
		}
		cards = append(cards, card)
	}

	if len(cards) == 0 {
		// The schema specifies 404 for Not Found in this context
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(RetrieveResponse{CardNumbers: []string{}})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(RetrieveResponse{CardNumbers: cards})
}

func main() {
	initDB()
	defer db.Close()

	// Ensure APP_SECRET is read if needed, though not used for logic here as per schema
	_ = os.Getenv("APP_SECRET")

	http.HandleFunc("/associate_card", associateCardHandler)
	http.HandleFunc("/retrieve_cards", retrieveCardsHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}