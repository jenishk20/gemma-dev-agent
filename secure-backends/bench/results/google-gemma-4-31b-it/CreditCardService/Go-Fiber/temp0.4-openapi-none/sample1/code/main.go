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
	statement := `CREATE TABLE IF NOT EXISTS associations (
		card_number TEXT,
		phone_number TEXT,
		PRIMARY KEY (card_number, phone_number)
	);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	app.Post("/associate_card", func(c *fiber.Ctx) error {
		req := new(AssociateRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).SendString("Invalid request")
		}

		if req.CreditCard == "" || req.Phone == "" {
			return c.Status(400).SendString("Credit card and phone are required")
		}

		_, err := db.Exec("INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)", req.CreditCard, req.Phone)
		if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		return c.SendStatus(201)
	})

	app.Post("/retrieve_cards", func(c *fiber.Ctx) error {
		req := new(RetrieveRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).SendString("Invalid request")
		}

		if len(req.PhoneNumbers) == 0 {
			return c.Status(400).SendString("Phone numbers list cannot be empty")
		}

		// To find cards associated with ALL provided phone numbers, 
		// we group by card_number and count if the number of distinct phone numbers 
		// associated with that card matches the number of requested phones.
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
			return c.Status(500).SendString("Internal server error")
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
			return c.Status(404).JSON(RetrieveResponse{CardNumbers: []string{}})
		}

		return c.JSON(RetrieveResponse{CardNumbers: cards})
	})

	// APP_SECRET is provided in env but not required for the logic of this specific schema
	_ = os.Getenv("APP_SECRET")

	log.Fatal(app.Listen("0.0.0.0:5000"))
}