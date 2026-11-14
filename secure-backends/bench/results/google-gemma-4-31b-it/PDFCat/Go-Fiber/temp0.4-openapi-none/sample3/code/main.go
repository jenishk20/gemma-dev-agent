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
		// Parse multipart form
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Invalid input or missing files.",
			})
		}

		files := form.File["files"]
		if len(files) == 0 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Invalid input or missing files.",
			})
		}

		// Create a temporary directory for this request to avoid collisions
		tempDir, err := os.MkdirTemp("", "pdf-concat-")
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "An error occurred while processing the files.",
			})
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			// Save uploaded file to temp directory
			filePath := filepath.Join(tempDir, fmt.Sprintf("input_%d.pdf", i))
			
			openFile, err := fileHeader.Open()
			if err != nil {
				return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
					"error": "Could not open uploaded file.",
				})
			}
			
			dstFile, err := os.Create(filePath)
			if err != nil {
				openFile.Close()
				return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"error": "Could not save uploaded file.",
				})
			}

			if _, err = io.Copy(dstFile, openFile); err != nil {
				openFile.Close()
				dstFile.Close()
				return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"error": "Failed to write file to disk.",
				})
			}
			openFile.Close()
			dstFile.Close()
			inputPaths = append(inputPaths, filePath)
		}

		// Define output path
		outputFileName := uuid.New().String() + ".pdf"
		outputPath := filepath.Join(tempDir, outputFileName)

		// Prepare pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
		args := append(inputPaths, outputPath)
		cmd := exec.Command("pdfunite", args...)
		
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "An error occurred while processing the files.",
			})
		}

		// Read the resulting PDF to send it back
		resultFile, err := os.Open(outputPath)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Could not read concatenated file.",
			})
		}
		defer resultFile.Close()

		c.Set("Content-Type", "application/pdf")
		return c.SendStream(resultFile)
	})

	app.Listen("0.0.0.0:5000")
}