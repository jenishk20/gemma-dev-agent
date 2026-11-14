package main

import (
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

func main() {
	app := fiber.New()

	app.Post("/convert", func(c *fiber.Ctx) error {
		// Retrieve the file from the multipart form
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Missing or invalid file upload",
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

		// Ensure temporary files are cleaned up after the request
		defer os.Remove(inputPath)
		defer os.Remove(outputPath)

		// Execute the pdftotext utility from poppler-utils
		// Command: pdftotext <input.pdf> <output.txt>
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

		// Return the content as plain text
		c.Set("Content-Type", "text/plain")
		return c.Send(content)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}