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
		http.Error(w, "credit_card and phone are required", http.StatusBadRequest)
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
		http.Error(w, "phone_numbers array cannot be empty", http.StatusBadRequest)
		return
	}

	// To find cards associated with ALL given phone numbers, we group by card 
	// and filter for those where the count of distinct phones matches the input list size.
	query := `
	SELECT credit_card 
	FROM associations 
	WHERE phone IN (` + placeholderList(len(req.PhoneNumbers)) + `) 
	GROUP BY credit_card 
	HAVING COUNT(DISTINCT phone) = ?`

	args := make([]interface{}, 0)
	for _, p := range req.PhoneNumbers {
		args = append(args, p)
	}
	args = append(args, len(req.PhoneNumbers))

	rows, err := db.Query(query, args...)
	if err != nil {
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
		// The schema says 404 for Not Found
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(RetrieveResponse{CardNumbers: []string{}})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(RetrieveResponse{CardNumbers: cards})
}

func placeholderList(n int) string {
	res := ""
	for i := 0; i < n; i++ {
		res += "?"
		if i < n-1 {
			res += ","
		}
	}
	return res
}

func main() {
	initDB()
	defer db.Close()

	// Ensure APP_SECRET is read if provided, though not used by the logic of the schema
	_ = os.Getenv("APP_SECRET")

	http.HandleFunc("/associate_card", associateCardHandler)
	http.HandleFunc("/retrieve_cards", retrieveCardsHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}