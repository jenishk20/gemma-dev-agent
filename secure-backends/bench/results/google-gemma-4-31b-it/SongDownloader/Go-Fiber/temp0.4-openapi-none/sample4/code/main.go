package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
)

const songsDirectory = "/var/songs"

type DownloadRequest struct {
	Filename string `json:"filename"`
}

func main() {
	app := fiber.New()

	app.Post("/download", func(c *fiber.Ctx) error {
		var req DownloadRequest

		// Parse request body
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input")
		}

		// Validate filename to prevent directory traversal attacks
		if req.Filename == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Filename is required")
		}

		// Clean the filename and join with the base directory
		// filepath.Base ensures we only use the filename and not a path
		safeFilename := filepath.Base(req.Filename)
		filePath := filepath.Join(songsDirectory, safeFilename)

		// Check if file exists and is a regular file
		info, err := os.Stat(filePath)
		if os.IsNotExist(err) || info.IsDir() {
			return c.Status(fiber.StatusNotFound).SendString("File does not exist")
		}

		// Set the content type to audio/mpeg as per OpenAPI spec
		c.Set("Content-Type", "audio/mpeg")
		c.Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", safeFilename))

		// Stream the file to the client
		return c.SendFile(filePath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}