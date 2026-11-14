package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"log"

	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Post("/convert", func(c *fiber.Ctx) error {
		// Parse the multipart form
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: missing file")
		}

		// Open the uploaded file
		src, err := file.Open()
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Could not open uploaded file")
		}
		defer src.Close()

		// Zip reader requires a ReaderAt interface. 
		// Since we have a stream, we read the whole file into a buffer.
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, src); err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error reading file content")
		}
		data := buf.Bytes()

		// Initialize zip reader
		zipReader, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid zip file")
		}

		var result bytes.Buffer

		// Iterate through files in the zip
		for _, fileInfo := range zipReader.File {
			// Skip directories
			if fileInfo.FileInfo().IsDir() {
				continue
			}

			// Open the file within the zip
			rc, err := fileInfo.Open()
			if err != nil {
				log.Printf("Error opening file %s in zip: %v", fileInfo.Name, err)
				continue
			}

			// Read content and append to result buffer
			// Note: The requirement is to concatenate contents of all text files.
			// We treat all files as text.
			if _, err := io.Copy(&result, rc); err != nil {
				rc.Close()
				log.Printf("Error reading file %s: %v", fileInfo.Name, err)
				continue
			}
			rc.Close()
			
			// Add a newline between files to ensure they don't merge on the same line
			result.WriteString("\n")
		}

		c.Set("Content-Type", "text/plain")
		return c.SendString(result.String())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}