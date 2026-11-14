package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"log"
	"net/http"
	"path/filepath"

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
		f, err := c.OpenBinary(file)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Could not open uploaded file")
		}
		defer f.Close()

		// Zip reader requires a ReaderAt, so we read the file into a buffer
		// Since we are dealing with zip files, we need the full byte slice
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, f); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Error reading file content")
		}
		data := buf.Bytes()

		// Initialize zip reader
		zipReader, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid zip file")
		}

		var result bytes.Buffer
		for _, fileInfo := range zipReader.File {
			// We only process files (not directories)
			if fileInfo.FileInfo().IsDir() {
				continue
			}

			// Open the file within the zip
			rc, err := fileInfo.Open()
			if err != nil {
				log.Printf("Error opening file %s in zip: %v", fileInfo.Name, err)
				continue
			}

			// Read content
			content, err := io.ReadAll(rc)
			rc.Close()
			if err != nil {
				log.Printf("Error reading file %s in zip: %v", fileInfo.Name, err)
				continue
			}

			// Append content to result buffer
			// We add a newline between files to ensure they are separated
			result.Write(content)
			if len(content) > 0 && content[len(content)-1] != '\n' {
				result.WriteByte('\n')
			}
		}

		c.Set("Content-Type", "text/plain")
		return c.Status(http.StatusOK).SendString(result.String())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}