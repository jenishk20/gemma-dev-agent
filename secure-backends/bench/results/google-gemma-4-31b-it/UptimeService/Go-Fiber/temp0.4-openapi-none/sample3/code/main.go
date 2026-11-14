package main

import (
	"database/sql"
	"log"
	"time"

	"github.com/gofiber/fiber/v2"
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

func main() {
	// Initialize SQLite database
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table for service monitoring
	statement := `
	CREATE TABLE IF NOT EXISTS services (
		service_id TEXT PRIMARY KEY,
		token TEXT,
		last_notification DATETIME
	);`
	if _, err := db.Exec(statement); err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// POST /heartbeat
	app.Post("/heartbeat", func(c *fiber.Ctx) error {
		var req HeartbeatRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request payload")
		}

		if req.ServiceID == "" || req.Token == "" {
			return c.Status(fiber.StatusBadRequest).SendString("serviceId and token are required")
		}

		now := time.Now()
		_, err := db.Exec(
			"INSERT INTO services (service_id, token, last_notification) VALUES (?, ?, ?) ON CONFLICT(service_id) DO UPDATE SET token=excluded.token, last_notification=excluded.last_notification",
			req.ServiceID, req.Token, now,
		)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
		}

		return c.SendStatus(fiber.StatusOK)
	})

	// POST /services
	app.Post("/services", func(c *fiber.Ctx) error {
		var req TokenRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request payload")
		}

		if req.Token == "" {
			return c.Status(fiber.StatusBadRequest).SendString("token is required")
		}

		rows, err := db.Query("SELECT service_id, last_notification FROM services WHERE token = ?", req.Token)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
		}
		defer rows.Close()

		var services []ServiceStatus
		for rows.Next() {
			var s ServiceStatus
			if err := rows.Scan(&s.ServiceID, &s.LastNotification); err != nil {
				return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
			}
			services = append(services, s)
		}

		if err = rows.Err(); err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
		}

		return c.JSON(services)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}