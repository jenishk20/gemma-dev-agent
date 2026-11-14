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
			c.JSON(http.StatusBadRequest, gin.H{"error": "Missing or invalid file in request"})
			return
		}

		// Validate that the file is a PDF based on extension
		if filepath.Ext(file.Filename) != ".pdf" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Only PDF files are supported"})
			return
		}

		// Create a unique temporary filename to avoid collisions
		tempID := uuid.New().String()
		tempInputPath := filepath.Join(os.TempDir(), tempID+".pdf")
		tempOutputPath := filepath.Join(os.TempDir(), tempID+".txt")

		// Save the uploaded file to the temporary directory
		if err := c.SaveUploadedFile(file, tempInputPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Failed to save upload: %v", err)})
			return
		}

		// Ensure temporary files are cleaned up after the request is handled
		defer os.Remove(tempInputPath)
		defer os.Remove(tempOutputPath)

		// Execute the pdftotext utility from poppler-utils
		// Command: pdftotext <input.pdf> <output.txt>
		cmd := exec.Command("pdftotext", tempInputPath, tempOutputPath)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("PDF conversion failed: %v", err)})
			return
		}

		// Read the resulting text file
		content, err := os.ReadFile(tempOutputPath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Failed to read converted text: %v", err)})
			return
		}

		// Return the content as plain text as specified in the OpenAPI schema
		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, string(content))
	})

	// Start the server on 0.0.0.0:5000
	r.Run("0.0.0.0:5000")
}