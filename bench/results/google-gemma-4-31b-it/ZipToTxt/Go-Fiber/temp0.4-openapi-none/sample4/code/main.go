package main

import (
	"archive/zip"
	"bytes"
	"io"
	"log"
	"strings"

	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Post("/convert", func(c *fiber.Ctx) error {
		// Parse the multipart form
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: file field is required")
		}

		// Open the uploaded file
		src, err := file.Open()
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Could not open uploaded file")
		}
		defer src.Close()

		// Zip.NewReader requires a ReaderAt, so we read the file into a buffer
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, src); err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error reading file content")
		}

		// Create a reader for the zip archive
		zipReader, err := zip.NewReader(bytes.NewReader(buf.Bytes()), int64(buf.Len()))
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid zip file")
		}

		var result strings.Builder

		// Iterate through files in the zip
		for _, fileInfo := range zipReader.File {
			// We only process files that are not directories
			if fileInfo.FileInfo().IsDir() {
				continue
			}

			// Open the file within the zip
			rc, err := fileInfo.Open()
			if err != nil {
				continue // Skip files that cannot be opened
			}

			// Read the content of the file
			content, err := io.ReadAll(rc)
			rc.Close()
			if err != nil {
				continue // Skip files that cannot be read
			}

			// Append content to the result builder
			result.Write(content)
			// Add a newline between files to ensure they are separated
			result.WriteString("\n")
		}

		return c.Status(fiber.StatusOK).SendString(result.String())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}