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
		// Get the file from the multipart form
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

		// Since archive/zip requires a ReaderAt, we read the file into a buffer
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, src); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Error reading file content"})
			return
		}
		byteData := buf.Bytes()

		// Open the zip archive
		zipReader, err := zip.NewReader(bytes.NewReader(byteData), int64(len(byteData)))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid zip file"})
			return
		}

		var resultBuffer bytes.Buffer

		// Iterate through files in the zip
		for _, file := range zipReader.File {
			// Skip directories
			if file.FileInfo().IsDir() {
				continue
			}

			// We consider files with .txt extension or no extension as text files
			// In a real-world scenario, we might check MIME types
			ext := filepath.Ext(file.Name)
			if ext != ".txt" && ext != "" {
				continue
			}

			rc, err := file.Open()
			if err != nil {
				continue // Skip files that cannot be opened
			}

			// Read content and write to result buffer
			if _, err := io.Copy(&resultBuffer, rc); err != nil {
				rc.Close()
				continue
			}
			rc.Close()

			// Add a newline between files if not already present to ensure separation
			resultBuffer.WriteString("\n")
		}

		// Return the concatenated text as plain text
		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, resultBuffer.String())
	})

	r.Run("0.0.0.0:5000")
}