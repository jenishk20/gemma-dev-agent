package main

import (
	"database/sql"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

type AssociateRequest struct {
	CreditCard string `json:"credit_card" binding:"required"`
	Phone      string `json:"phone" binding:"required"`
}

type RetrieveRequest struct {
	PhoneNumbers []string `json:"phone_numbers" binding:"required"`
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

func associateCard(c *gin.Context) {
	var req AssociateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	_, err := db.Exec("INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)", req.CreditCard, req.Phone)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
		return
	}

	c.Status(http.StatusCreated)
}

func retrieveCards(c *gin.Context) {
	var req RetrieveRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	if len(req.PhoneNumbers) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "phone_numbers list cannot be empty"})
		return
	}

	// We need cards that are associated with ALL the provided phone numbers.
	// We group by card_number and count if the number of distinct phone numbers matching the list equals the list length.
	query := `
		SELECT card_number 
		FROM associations 
		WHERE phone_number IN (`
	
	// Build placeholders for the IN clause
	placeholders := ""
	args := make([]interface{}, 0)
	for i, phone := range req.PhoneNumbers {
		if i > 0 {
			placeholders += ","
		}
		placeholders += "?"
		args = append(args, phone)
	}
	query += placeholders + `) 
		GROUP BY card_number 
		HAVING COUNT(DISTINCT phone_number) = ?`
	
	args = append(args, len(req.PhoneNumbers))

	rows, err := db.Query(query, args...)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
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
		c.JSON(http.StatusNotFound, gin.H{"error": "No cards found"})
		return
	}

	c.JSON(http.StatusOK, RetrieveResponse{CardNumbers: cards})
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	r.POST("/associate_card", associateCard)
	r.POST("/retrieve_cards", retrieveCards)

	r.Run("0.0.0.0:5000")
}