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
		// Get the file from the multipart form
		fileHeader, err := c.FormFile("file")
		if err != nil {
			c.String(http.StatusBadRequest, "Invalid input: file is required")
			return
		}

		// Open the uploaded file
		file, err := fileHeader.Open()
		if err != nil {
			c.String(http.StatusBadRequest, "Could not open uploaded file")
			return
		}
		defer file.Close()

		// Since zip.NewReader requires a ReaderAt, we read the file into a buffer
		// In a production environment with huge files, we would save to a temp file first.
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, file); err != nil {
			c.String(http.StatusBadRequest, "Error reading file content")
			return
		}
		data := buf.Bytes()

		// Open the zip archive
		zipReader, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
		if err != nil {
			c.String(http.StatusBadRequest, "Invalid zip file")
			return
		}

		var result strings.Builder

		// Iterate through files in the zip
		for _, f := range zipReader.File {
			// Skip directories
			if f.FileInfo().IsDir() {
				continue
			}

			// Only process files that look like text files (basic check by extension)
			// The prompt asks to concatenate contents of all text files.
			if isTextFile(f.Name) {
				rc, err := f.Open()
				if err != nil {
					continue // Skip files that cannot be opened
				}

				// Read content of the file
				content, err := io.ReadAll(rc)
				rc.Close()
				if err != nil {
					continue
				}

				// Append content to the final string
				result.Write(content)
				// Ensure there is a newline between files if not present
				if len(content) > 0 && content[len(content)-1] != '\n' {
					result.WriteString("\n")
				}
			}
		}

		c.String(http.StatusOK, result.String())
	})

	r.Run("0.0.0.0:5000")
}

// isTextFile checks if the file extension is commonly associated with text files
func isTextFile(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	textExtensions := map[string]bool{
		".txt":  true,
		".md":   true,
		".json": true,
		".xml":  true,
		".csv":  true,
		".log":  true,
		".html": true,
		".css":  true,
		".js":   true,
		".py":   true,
		".go":   true,
		".c":    true,
		".cpp":  true,
		".h":    true,
	}
	// If it has no extension, we treat it as text, otherwise check the map
	if ext == "" {
		return true
	}
	return textExtensions[ext]
}