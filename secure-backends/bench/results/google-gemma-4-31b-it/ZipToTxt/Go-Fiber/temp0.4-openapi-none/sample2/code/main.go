package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"log"
	"net/http"
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
			return c.Status(fiber.StatusInternalServerError).SendString("Error opening uploaded file")
		}
		defer src.Close()

		// Zip.NewReader requires a ReaderAt. Since the uploaded file is a stream, 
		// we read it into a buffer first.
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, src); err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error reading file content")
		}

		// Create a reader for the zip archive
		zipReader, err := zip.NewReader(&buf, int64(buf.Len()))
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid zip file")
		}

		var result strings.Builder

		// Iterate through files in the zip
		for _, f := range zipReader.File {
			// We only process files that are not directories and have a .txt extension
			// or are generally treated as text. For this implementation, we check for .txt
			if f.FileInfo().IsDir() {
				continue
			}

			// Check if the file is a text file based on extension
			if strings.ToLower(f.Name) == "" || !strings.HasSuffix(strings.ToLower(f.Name), ".txt") {
				continue
			}

			rc, err := f.Open()
			if err != nil {
				log.Printf("Error opening file %s in zip: %v", f.Name, err)
				continue
			}

			// Read content of the text file
			content, err := io.ReadAll(rc)
			rc.Close()
			if err != nil {
				log.Printf("Error reading file %s in zip: %v", f.Name, err)
				continue
			}

			result.Write(content)
			result.WriteString("\n") // Ensure separation between files
		}

		return c.Status(http.StatusOK).ContentType("text/plain").SendString(result.String())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}