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

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS services (
		service_id TEXT PRIMARY KEY,
		token TEXT,
		last_notification DATETIME
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

	app.Post("/heartbeat", func(c *fiber.Ctx) error {
		req := new(HeartbeatRequest)
		if err := c.BodyParser(req); err != nil {
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

	app.Post("/services", func(c *fiber.Ctx) error {
		req := new(TokenRequest)
		if err := c.BodyParser(req); err != nil {
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
			var lastNotif string
			if err := rows.Scan(&s.ServiceID, &lastNotif); err != nil {
				return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
			}
			
			// SQLite stores dates as strings or ints. Parse the string back to time.Time.
			t, err := time.Parse("2006-01-02 15:04:05.999999999", lastNotif)
			if err != nil {
				// Fallback for different sqlite date formats
				t, _ = time.Parse("2006-01-02 15:04:05", lastNotif)
			}
			s.LastNotification = t
			services = append(services, s)
		}

		if services == nil {
			services = []ServiceStatus{}
		}

		return c.JSON(services)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}