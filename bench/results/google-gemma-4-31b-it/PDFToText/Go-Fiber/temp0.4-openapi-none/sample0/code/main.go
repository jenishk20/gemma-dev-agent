package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"

	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Post("/convert", func(c *fiber.Ctx) error {
		// Retrieve the file from the multipart form request
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Missing or invalid file upload",
			})
		}

		// Save the uploaded file to a temporary location
		tempInputPath := fmt.Sprintf("temp_%s.pdf", file.Filename)
		if err := c.SaveFile(file, tempInputPath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to save uploaded file",
			})
		}
		// Ensure temporary file is cleaned up
		defer os.Remove(tempInputPath)

		// Define a temporary output file for pdftotext
		tempOutputPath := tempInputPath + ".txt"
		defer os.Remove(tempOutputPath)

		// Execute the pdftotext utility from poppler-utils
		// Usage: pdftotext [input-pdf] [output-text-file]
		cmd := exec.Command("pdftotext", tempInputPath, tempOutputPath)
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "PDF conversion failed",
			})
		}

		// Read the resulting text file
		content, err := os.ReadFile(tempOutputPath)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to read converted text",
			})
		}

		// Return the content as plain text as per OpenAPI spec
		c.Set("Content-Type", "text/plain")
		return c.SendString(string(content))
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}