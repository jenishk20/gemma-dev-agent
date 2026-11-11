package main

import (
	"archive/zip"
	"bytes"
	"io"
	"net/http"
	"path/filepath"

	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()

	r.POST("/convert", func(c *gin.Context) {
		// Get the file from the multipart form request
		fileHeader, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input: file is required"})
			return
		}

		// Open the uploaded file
		src, err := fileHeader.Open()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not open uploaded file"})
			return
		}
		defer src.Close()

		// Since zip.NewReader requires a ReaderAt, we read the file into a buffer
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, src); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Error reading file content"})
			return
		}
		byteData := buf.Bytes()

		// Initialize zip reader
		reader, err := zip.NewReader(bytes.NewReader(byteData), int64(len(byteData)))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid zip file"})
			return
		}

		var combinedText bytes.Buffer

		// Iterate through files in the zip archive
		for _, f := range reader.Files {
			// Only process files (not directories) and check if they are text files
			// We use a simple check for .txt extension as per common "text file" definition
			if f.FileInfo().IsDir() || filepath.Ext(f.Name) != ".txt" {
				continue
			}

			rc, err := f.Open()
			if err != nil {
				continue // Skip files that cannot be opened
			}

			// Read content and write to the combined buffer
			if _, err := io.Copy(&combinedText, rc); err != nil {
				rc.Close()
				continue
			}
			rc.Close()

			// Add a newline between files to ensure they don't merge on the same line
			combinedText.WriteString("\n")
		}

		// Return the concatenated text as plain text
		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, combinedText.String())
	})

	r.Run("0.0.0.0:5000")
}