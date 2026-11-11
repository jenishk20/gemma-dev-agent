package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func main() {
	r := gin.Default()

	r.POST("/convert", func(c *gin.Context) {
		// Retrieve the file from the multipart form request
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Missing file in request"})
			return
		}

		// Validate file extension
		if filepath.Ext(file.Filename) != ".pdf" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Uploaded file must be a PDF"})
			return
		}

		// Create a unique temporary filename to avoid collisions
		tempID := uuid.New().String()
		inputPath := filepath.Join(os.TempDir(), tempID+".pdf")
		outputPath := filepath.Join(os.TempDir(), tempID+".txt")

		// Save the uploaded file to disk
		if err := c.SaveUploadedFile(file, inputPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded file"})
			return
		}

		// Ensure cleanup of temporary files
		defer func() {
			os.Remove(inputPath)
			os.Remove(outputPath)
		}()

		// Execute pdftotext utility
		// Usage: pdftotext [input-pdf] [output-txt]
		cmd := exec.Command("pdftotext", inputPath, outputPath)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Conversion failed: %v", err)})
			return
		}

		// Read the generated text file
		content, err := os.ReadFile(outputPath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read converted text"})
			return
		}

		// Return the content as plain text as per OpenAPI schema
		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, string(content))
	})

	// Start the server on 0.0.0.0:5000
	r.Run("0.0.0.0:5000")
}