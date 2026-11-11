package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
)

const songsDir = "/var/songs"

type DownloadRequest struct {
	Filename string `json:"filename"`
}

func main() {
	app := fiber.New()

	app.Post("/download", func(c *fiber.Ctx) error {
		var req DownloadRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Invalid input",
			})
		}

		if req.Filename == "" {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Filename is required",
			})
		}

		// Prevent directory traversal attacks by taking only the base name
		safePath := filepath.Join(songsDir, filepath.Base(req.Filename))

		// Check if file exists and is a regular file
		info, err := os.Stat(safePath)
		if os.IsNotExist(err) || info.IsDir() {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": "File does not exist",
			})
		}

		// Set the content type to audio/mpeg as per OpenAPI spec
		c.Set("Content-Type", "audio/mpeg")
		c.Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", filepath.Base(safePath)))

		// Stream the file to the client
		return c.SendFile(safePath)
	})

	log.Fatal(app.Listen(":5000"))
}