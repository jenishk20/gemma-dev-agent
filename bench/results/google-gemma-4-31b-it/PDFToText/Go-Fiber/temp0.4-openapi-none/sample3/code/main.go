package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

func main() {
	app := fiber.New()

	app.Post("/convert", func(c *fiber.Ctx) error {
		// Get the file from the multipart form
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Missing or invalid file in request",
			})
		}

		// Create a unique temporary filename to avoid collisions
		tempID := uuid.New().String()
		inputPath := filepath.Join(os.TempDir(), tempID+".pdf")
		outputPath := filepath.Join(os.TempDir(), tempID+".txt")

		// Save the uploaded file to disk
		if err := c.SaveFile(file, inputPath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to save uploaded file",
			})
		}

		// Ensure cleanup of temporary files
		defer os.Remove(inputPath)
		defer os.Remove(outputPath)

		// Execute pdftotext utility
		// Command: pdftotext <input_pdf> <output_txt>
		cmd := exec.Command("pdftotext", inputPath, outputPath)
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": fmt.Sprintf("PDF conversion failed: %v", err),
			})
		}

		// Read the resulting text file
		content, err := os.ReadFile(outputPath)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to read converted text",
			})
		}

		// Return as plain text as per OpenAPI spec
		c.Set("Content-Type", "text/plain")
		return c.Send(content)
	})

	// Start server on 0.0.0.0:5000
	app.Listen(":5000")
}