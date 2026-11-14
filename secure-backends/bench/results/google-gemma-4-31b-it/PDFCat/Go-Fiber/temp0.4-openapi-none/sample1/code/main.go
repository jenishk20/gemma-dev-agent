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

	app.Post("/concatenate", func(c *fiber.Ctx) error {
		// Get the files from the multipart form request
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input or missing files."})
		}

		files := form.File["files"]
		if len(files) == 0 {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input or missing files."})
		}

		// Create a temporary directory to store uploaded files
		tempDir, err := os.MkdirTemp("", "pdf-concat-")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "An error occurred while processing the files."})
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			// Save each uploaded file to the temp directory
			filePath := filepath.Join(tempDir, fmt.Sprintf("input_%d.pdf", i))
			if err := c.SaveFile(fileHeader, filePath); err != nil {
				return c.Status(500).JSON(fiber.Map{"error": "An error occurred while processing the files."})
			}
			inputPaths = append(inputPaths, filePath)
		}

		// Define the output path for the concatenated PDF
		outputFileName := fmt.Sprintf("output_%s.pdf", uuid.New().String())
		outputPath := filepath.Join(tempDir, outputFileName)

		// Prepare the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
		args := append(inputPaths, outputPath)
		cmd := exec.Command("pdfunite", args...)

		if err := cmd.Run(); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "An error occurred while processing the files."})
		}

		// Read the resulting PDF file
		resultFile, err := os.Open(outputPath)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "An error occurred while processing the files."})
		}
		defer resultFile.Close()

		// Set headers and stream the file back to the client
		c.Set("Content-Type", "application/pdf")
		c.Set("Content-Disposition", "attachment; filename=concatenated.pdf")

		// Use fiber's SendFile or manually stream
		return c.SendFile(outputPath)
	})

	app.Listen(":5000")
}