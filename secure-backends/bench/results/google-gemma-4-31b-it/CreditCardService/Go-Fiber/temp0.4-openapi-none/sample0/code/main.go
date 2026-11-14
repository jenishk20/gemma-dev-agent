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
		credit_card TEXT,
		phone TEXT,
		PRIMARY KEY (credit_card, phone)
	);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	app.Post("/associate_card", func(c *fiber.Ctx) error {
		req := new(AssociateRequest)
		if err := c.RequestBodyParser(req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request")
		}

		if req.CreditCard == "" || req.Phone == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Missing credit_card or phone")
		}

		_, err := db.Exec("INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)", req.CreditCard, req.Phone)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString(err.Error())
		}

		return c.SendStatus(fiber.StatusCreated)
	})

	app.Post("/retrieve_cards", func(c *fiber.Ctx) error {
		req := new(RetrieveRequest)
		if err := c.RequestBodyParser(req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request")
		}

		if len(req.PhoneNumbers) == 0 {
			return c.Status(fiber.StatusBadRequest).SendString("phone_numbers array cannot be empty")
		}

		// To find cards associated with ALL given phone numbers:
		// We group by credit_card and count how many of the requested phones match.
		// If the count equals the length of the input array, the card is associated with all.
		
		// Constructing the query dynamically for the IN clause
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
			return c.Status(fiber.StatusInternalServerError).SendString(err.Error())
		}
		defer rows.Close()

		var cards []string
		for rows.Next() {
			var card string
			if err := rows.Scan(&card); err != nil {
				return c.Status(fiber.StatusInternalServerError).SendString(err.Error())
			}
			cards = append(cards, card)
		}

		if len(cards) == 0 {
			return c.Status(fiber.StatusNotFound).JSON(RetrieveResponse{CardNumbers: []string{}})
		}

		return c.JSON(RetrieveResponse{CardNumbers: cards})
	})

	// Use APP_SECRET if provided, though not explicitly required for logic here
	_ = os.Getenv("APP_SECRET")

	log.Fatal(app.Listen("0.0.0.0:5000"))
}