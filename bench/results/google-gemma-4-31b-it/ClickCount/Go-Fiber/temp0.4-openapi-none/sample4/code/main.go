package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

type Click struct {
	ID        string    `json:"id"`
	Timestamp time.Time `json:"timestamp"`
}

func main() {
	// Initialize SQLite database
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table
	statement := `CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// POST /click - Register a click
	app.Post("/click", func(c *fiber.Ctx) error {
		id := uuid.New().String()
		now := time.Now().UTC()

		_, err := db.Exec("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", id, now)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request")
		}

		return c.SendStatus(fiber.StatusCreated)
	})

	// GET /clicks - Retrieve clicks based on date and direction
	app.Get("/clicks", func(c *fiber.Ctx) error {
		dateStr := c.Query("date")
		direction := c.Query("direction")

		if dateStr == "" || direction == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request: date and direction are required")
		}

		// Validate direction enum
		validDirections := map[string]bool{"<": true, ">": true, "<=": true, ">=": true}
		if !validDirections[direction] {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request: direction must be <, >, <=, or >=")
		}

		// Parse date to ensure it's valid (YYYY-MM-DD)
		_, err := time.Parse("2006-01-02", dateStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request: date must be in YYYY-MM-DD format")
		}

		// Query database
		// Note: Using fmt.Sprintf for the operator is safe here because we validated against a strict whitelist
		query := fmt.Sprintf("SELECT id, timestamp FROM clicks WHERE timestamp %s ?", direction)
		rows, err := db.Query(query, dateStr)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
		}
		defer rows.Close()

		var clicks []Click
		for rows.Next() {
			var cl Click
			var ts string
			if err := rows.Scan(&cl.ID, &ts); err != nil {
				continue
			}
			// SQLite stores dates as strings, parse back to time.Time
			parsedTime, err := time.Parse("2006-01-02 15:04:05", ts)
			if err != nil {
				// Try alternative SQLite format if necessary
				parsedTime, _ = time.Parse(time.RFC3339, ts)
			}
			cl.Timestamp = parsedTime
			clicks = append(clicks, cl)
		}

		if len(clicks) == 0 {
			return c.Status(fiber.StatusNotFound).SendString("No clicks found")
		}

		return c.JSON(clicks)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}