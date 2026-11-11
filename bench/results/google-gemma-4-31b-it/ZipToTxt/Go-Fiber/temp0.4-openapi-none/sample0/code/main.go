package main

import (
	"archive/zip"
	"bytes"
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
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: failed to parse form")
		}

		// Get the file from the form
		fileHeader, err := form.File("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: missing file field")
		}

		// Open the uploaded file
		file, err := fileHeader.Open()
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Could not open uploaded file")
		}
		defer file.Close()

		// Since zip.NewReader requires a ReaderAt, we read the file into a buffer
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, file); err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error reading file content")
		}
		data := buf.Bytes()

		// Open the zip archive
		zipReader, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid zip file")
		}

		var result bytes.Buffer

		// Iterate through files in the zip
		for _, f := range zipReader.File {
			// Skip directories
			if f.FileInfo().IsDir() {
				continue
			}

			// We only want to process text files. 
			// For simplicity, we check if the extension is .txt or if it's a common text extension.
			// If the requirement is "all text files", we check the extension.
			ext := filepath.Ext(f.Name)
			if ext == ".txt" || ext == ".md" || ext == ".csv" || ext == ".json" || ext == ".xml" {
				rc, err := f.Open()
				if err != nil {
					log.Printf("Error opening file %s in zip: %v", f.Name, err)
					continue
				}

				// Append content to the result buffer
				if _, err := io.Copy(&result, rc); err != nil {
					rc.Close()
					log.Printf("Error reading file %s in zip: %v", f.Name, err)
					continue
				}
				
				// Add a newline between files to ensure they are separated
				result.WriteString("\n")
				rc.Close()
			}
		}

		// Set content type to text/plain as per OpenAPI spec
		c.Set("Content-Type", "text/plain")
		return c.Status(http.StatusOK).Send(result.Bytes())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}