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
		req := new(DownloadRequest)

		// Parse request body
		if err := c.BodyParser(req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input")
		}

		// Validate filename to prevent directory traversal attacks
		if req.Filename == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Filename is required")
		}

		// Clean the filename to prevent path traversal (e.g., ../../etc/passwd)
		safeFilename := filepath.Base(req.Filename)
		filePath := filepath.Join(songsDir, safeFilename)

		// Check if file exists and is accessible
		if _, err := os.Stat(filePath); os.IsNotExist(err) {
			return c.Status(fiber.StatusNotFound).SendString("File does not exist")
		}

		// Open the file for streaming
		file, err := os.Open(filePath)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error opening file")
		}
		defer file.Close()

		// Set the content type to audio/mpeg as per OpenAPI spec
		c.Set("Content-Type", "audio/mpeg")
		c.Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", safeFilename))

		// Stream the file content to the user
		return c.SendFile(filePath)
	})

	// Start the webserver on port 0.0.0.0:5000
	if err := app.Listen("0.0.0.0:5000"); err != nil {
		fmt.Printf("Error starting server: %v\n", err)
	}
}