package main

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
)

type DownloadRequest struct {
	Filename string `json:"filename"`
}

func main() {
	app := fiber.New()

	// The songs are stored in the /var/songs directory
	const songsDir = "/var/songs"

	app.Post("/download", func(c *fiber.Ctx) error {
		var req DownloadRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input")
		}

		if req.Filename == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Filename is required")
		}

		// Prevent directory traversal attacks by cleaning the path and checking the base
		safeFilename := filepath.Base(req.Filename)
		filePath := filepath.Join(songsDir, safeFilename)

		// Check if file exists and is not a directory
		info, err := os.Stat(filePath)
		if os.IsNotExist(err) || info.IsDir() {
			return c.Status(fiber.StatusNotFound).SendString("File does not exist")
		}

		// Set the content type to audio/mpeg as per OpenAPI spec
		c.Set("Content-Type", "audio/mpeg")
		c.Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", safeFilename))

		// Stream the file content
		return c.SendFile(filePath)
	})

	err := app.Listen("0.0.0.0:5000")
	if err != nil {
		fmt.Printf("Error starting server: %v\n", err)
	}
}