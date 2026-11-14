package main

import (
	"archive/zip"
	"bytes"
	"io"
	"net/http"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()

	r.POST("/convert", func(c *gin.Context) {
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input: file field is required"})
			return
		}

		// Open the uploaded file
		openedFile, err := file.Open()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not open uploaded file"})
			return
		}
		defer openedFile.Close()

		// Since zip.NewReader requires a ReaderAt, we read the file into memory.
		// For very large files, one would normally save to a temp file on disk.
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, openedFile); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read file content"})
			return
		}
		data := buf.Bytes()

		zipReader, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid zip file"})
			return
		}

		var result strings.Builder

		for _, f := range zipReader.File {
			// Skip directories
			if f.FileInfo().IsDir() {
				continue
			}

			// Only process files that have a text-like extension or are explicitly .txt
			// In a real scenario, we might check MIME types, but based on requirements:
			if filepath.Ext(f.Name) == ".txt" || isTextFile(f.Name) {
				rc, err := f.Open()
				if err != nil {
					continue // Skip files that cannot be opened
				}

				content, err := io.ReadAll(rc)
				rc.Close()
				if err != nil {
					continue
				}

				result.Write(content)
				result.WriteString("\n") // Ensure separation between files
			}
		}

		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, result.String())
	})

	r.Run("0.0.0.0:5000")
}

func isTextFile(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	textExtensions := map[string]bool{
		".txt":  true,
		".md":   true,
		".csv":  true,
		".json": true,
		".xml":  true,
		".log":  true,
	}
	return textExtensions[ext]
}