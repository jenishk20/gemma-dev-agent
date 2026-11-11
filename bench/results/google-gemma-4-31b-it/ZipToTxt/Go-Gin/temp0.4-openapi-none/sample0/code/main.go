package main

import (
	"archive/zip"
	"bytes"
	"fmt"
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
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input: file is required"})
			return
		}

		// Open the uploaded file
		openedFile, err := file.Open()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not open file"})
			return
		}
		defer openedFile.Close()

		// Since zip.NewReader requires a ReaderAt, we read the file into a buffer
		var buf bytes.Buffer
		if _, err := io.Copy(&buf, openedFile); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Error reading file"})
			return
		}

		// Create a reader for the zip archive
		zipReader, err := zip.NewReader(bytes.NewReader(buf.Bytes()), int64(buf.Len()))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid zip file"})
			return
		}

		var result strings.Builder

		for _, f := range zipReader.File {
			// Only process files (not directories) and check if they are text files
			if f.FileInfo().IsDir() {
				continue
			}

			// Simple check for text files based on extension
			ext := strings.ToLower(filepath.Ext(f.Name))
			if ext != ".txt" && ext != ".md" && ext != ".json" && ext != ".xml" && ext != ".csv" && ext != ".log" {
				// If we want to be strict about "text files", we check extension. 
				// If we want to be permissive, we could try to read everything.
				// Given the prompt "contents of all text files", we filter for common text extensions.
				continue
			}

			rc, err := f.Open()
			if err != nil {
				continue // Skip files that can't be opened
			}

			content, err := io.ReadAll(rc)
			rc.Close()
			if err != nil {
				continue
			}

			result.Write(content)
			result.WriteString("\n") // Add newline between files
		}

		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, result.String())
	})

	r.Run("0.0.0.0:5000")
}