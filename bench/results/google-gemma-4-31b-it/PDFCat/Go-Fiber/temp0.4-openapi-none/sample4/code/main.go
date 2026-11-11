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

	app.Post("/concatenate", func(c *fiber.Ctx) error {
		// Parse multipart form
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Invalid input or missing files.",
			})
		}

		files := form.Files["files"]
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
			
			src, err := fileHeader.Open()
			if err != nil {
				return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"error": "An error occurred while processing the files.",
				})
			}
			
			dst, err := os.Create(filePath)
			if err != nil {
				src.Close()
				return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"error": "An error occurred while processing the files.",
				})
			}

			if _, err = io.Copy(dst, src); err != nil {
				src.Close()
				dst.Close()
				return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"error": "An error occurred while processing the files.",
				})
			}
			src.Close()
			dst.Close()
			inputPaths = append(inputPaths, filePath)
		}

		// Generate output path
		outputFileName := uuid.New().String() + ".pdf"
		outputPath := filepath.Join(tempDir, outputFileName)

		// Construct pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
		args := append(inputPaths, outputPath)
		cmd := exec.Command("pdfunite", args...)
		
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "An error occurred while processing the files.",
			})
		}

		// Read the resulting PDF to send back to client
		resultFile, err := os.Open(outputPath)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "An error occurred while processing the files.",
			})
		}
		defer resultFile.Close()

		c.Set("Content-Type", "application/pdf")
		c.Set("Content-Disposition", "attachment; filename=concatenated.pdf")
		
		return c.SendStream(resultFile)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}