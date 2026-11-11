package main

import (
	"fmt"
	"os"

	"github.com/gofiber/fiber/v2"
)

type LogRequest struct {
	Message string `json:"message"`
}

const logFile = "logs.txt"

func main() {
	app := fiber.New()

	// POST /log - Log a message to the server
	app.Post("/log", func(c *fiber.Ctx) error {
		var req LogRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid request body")
		}

		// Open file in append mode, create if it doesn't exist
		f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Could not open log file")
		}
		defer f.Close()

		if _, err := f.WriteString(req.Message + "\n"); err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Could not write to log file")
		}

		return c.SendStatus(fiber.StatusOK)
	})

	// GET /logs - Retrieve all logged messages
	app.Get("/logs", func(c *fiber.Ctx) error {
		content, err := os.ReadFile(logFile)
		if err != nil {
			// If file doesn't exist yet, return empty string
			if os.IsNotExist(err) {
				return c.SendString("")
			}
			return c.Status(fiber.StatusInternalServerError).SendString("Could not read log file")
		}

		return c.Set("Content-Type", "text/plain").SendString(string(content))
	})

	fmt.Println("Server starting on 0.0.0.0:5000")
	if err := app.Listen("0.0.0.0:5000"); err != nil {
		fmt.Printf("Error starting server: %v\n", err)
	}
}