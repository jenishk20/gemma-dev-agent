package main

import (
	"database/sql"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
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

func main() {
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table for associations
	createTableSQL := `CREATE TABLE IF NOT EXISTS card_phone (
		card_number TEXT,
		phone_number TEXT,
		PRIMARY KEY (card_number, phone_number)
	);`
	if _, err := db.Exec(createTableSQL); err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	app.Post("/associate_card", func(c *fiber.Ctx) error {
		req := new(AssociateRequest)
		if err := c.RequestBody().UnmarshalJSON(req); err != nil {
			return c.Status(400).SendString("Invalid request")
		}

		if req.CreditCard == "" || req.Phone == "" {
			return c.Status(400).SendString("credit_card and phone are required")
		}

		_, err := db.Exec("INSERT OR IGNORE INTO card_phone (card_number, phone_number) VALUES (?, ?)", req.CreditCard, req.Phone)
		if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		return c.SendStatus(201)
	})

	app.Post("/retrieve_cards", func(c *fiber.Ctx) error {
		req := new(RetrieveRequest)
		if err := c.RequestBody().UnmarshalJSON(req); err != nil {
			return c.Status(400).SendString("Invalid request")
		}

		if len(req.PhoneNumbers) == 0 {
			return c.Status(400).SendString("phone_numbers array is required and cannot be empty")
		}

		// Find cards associated with ALL provided phone numbers
		// We group by card_number and count if the number of distinct phone numbers matches the input length
		query := `
			SELECT card_number 
			FROM card_phone 
			WHERE phone_number IN (` + 
			placeholderList(len(req.PhoneNumbers)) + 
			`) 
			GROUP BY card_number 
			HAVING COUNT(DISTINCT phone_number) = ?`

		args := make([]interface{}, 0)
		for _, p := range req.PhoneNumbers {
			args = append(args, p)
		}
		args = append(args, len(req.PhoneNumbers))

		rows, err := db.Query(query, args...)
		if err != nil {
			return c.Status(500).SendString("Internal server error")
		}
		defer rows.Close()

		var cards []string
		for rows.Next() {
			var card string
			if err := rows.Scan(&card); err != nil {
				return c.Status(500).SendString("Internal server error")
			}
			cards = append(cards, card)
		}

		if len(cards) == 0 {
			return c.Status(404).JSON(RetrieveResponse{CardNumbers: []string{}})
		}

		return c.JSON(RetrieveResponse{CardNumbers: cards})
	})

	// Use APP_SECRET if provided, though not strictly needed for this logic
	_ = os.Getenv("APP_SECRET")

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

func placeholderList(n int) string {
	if n == 0 {
		return ""
	}
	res := "?"
	for i := 1; i < n; i++ {
		res += "," + "?"
	}
	return res
}