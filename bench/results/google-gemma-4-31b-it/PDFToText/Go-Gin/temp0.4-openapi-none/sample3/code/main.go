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
	router := gin.Default()

	router.POST("/convert", func(c *gin.Context) {
		// Retrieve file from multipart form
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input or missing file"})
			return
		}

		// Validate file extension
		if filepath.Ext(file.Filename) != ".pdf" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Only PDF files are allowed"})
			return
		}

		// Create a unique temporary filename to avoid collisions
		tempID := uuid.New().String()
		tempInputPath := filepath.Join(os.TempDir(), tempID+".pdf")
		tempOutputPath := filepath.Join(os.TempDir(), tempID+".txt")

		// Save the uploaded file to disk
		if err := c.SaveUploadedFile(file, tempInputPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded file"})
			return
		}

		// Ensure cleanup of temporary files
		defer func() {
			os.Remove(tempInputPath)
			os.Remove(tempOutputPath)
		}()

		// Execute pdftotext utility
		// Command: pdftotext <input_pdf> <output_txt>
		cmd := exec.Command("pdftotext", tempInputPath, tempOutputPath)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Conversion failed"})
			return
		}

		// Read the resulting text file
		content, err := os.ReadFile(tempOutputPath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read converted text"})
			return
		}

		// Return the plain text content
		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, string(content))
	})

	// Start the server on 0.0.0.0:5000
	router.Run("0.0.0.0:5000")
}