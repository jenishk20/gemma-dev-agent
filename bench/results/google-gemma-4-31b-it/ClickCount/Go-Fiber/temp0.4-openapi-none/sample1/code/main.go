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

func main() {
	initDB()
	defer db.Close()

	app := fiber.New()

	// POST /click - Register a click
	app.Post("/click", func(c *fiber.Ctx) error {
		id := uuid.New().String()
		timestamp := time.Now()

		_, err := db.Exec("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", id, timestamp)
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

		// Use fmt.Sprintf for the operator as it cannot be parameterized in SQL
		query := fmt.Sprintf("SELECT id, timestamp FROM clicks WHERE timestamp %s ?", direction)
		rows, err := db.Query(query, dateStr)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Database error")
		}
		defer rows.Close()

		var clicks []Click
		for rows.Next() {
			var cl Click
			var ts string
			if err := rows.Scan(&cl.ID, &ts); err != nil {
				continue
			}
			// SQLite date handling
			cl.Timestamp, _ = time.Parse("2006-01-02 15:04:05", ts)
			if cl.Timestamp.IsZero() {
				// Try parsing as RFC3339 or other formats if necessary, 
				// but sqlite3 driver usually returns "YYYY-MM-DD HH:MM:SS"
				cl.Timestamp, _ = time.Parse(time.RFC3339, ts)
			}
			clicks = append(clicks, cl)
		}

		if len(clicks) == 0 {
			return c.Status(fiber.StatusNotFound).SendString("No clicks found")
		}

		return c.JSON(clicks)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}