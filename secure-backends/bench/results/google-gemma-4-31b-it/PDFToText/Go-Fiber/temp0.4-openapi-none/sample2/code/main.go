package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

func main() {
	app := fiber.New()

	app.Post("/convert", func(c *fiber.Ctx) error {
		// Retrieve the file from the multipart form data
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Missing or invalid file upload",
			})
		}

		// Create a unique temporary filename to avoid collisions
		tempDir := os.TempDir()
		tempFileName := uuid.New().String() + ".pdf"
		tempFilePath := filepath.Join(tempDir, tempFileName)

		// Save the uploaded file to the temporary path
		if err := c.SaveFile(file, tempFilePath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to save uploaded file",
			})
		}

		// Ensure the temporary file is deleted after processing
		defer os.Remove(tempFilePath)

		// Execute the pdftotext utility
		// pdftotext [options] <PDF-file> [-]
		// The "-" argument tells pdftotext to output to stdout instead of a file
		cmd := exec.Command("pdftotext", tempFilePath, "-")
		output, err := cmd.CombinedOutput()
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": fmt.Sprintf("PDF conversion failed: %v", err),
			})
		}

		// Return the extracted text as plain text
		c.Set("Content-Type", "text/plain")
		return c.Send(output)
	})

	app.Listen(":5000")
}