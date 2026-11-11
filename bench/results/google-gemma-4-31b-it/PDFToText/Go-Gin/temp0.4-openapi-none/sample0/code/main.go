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

		// Ensure the uploaded file is a PDF
		if filepath.Ext(file.Filename) != ".pdf" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Only PDF files are allowed"})
			return
		}

		// Create a temporary file to store the uploaded PDF
		tempID := uuid.New().String()
		tempInputPath := filepath.Join(os.TempDir(), tempID+".pdf")
		tempOutputPath := filepath.Join(os.TempDir(), tempID+".txt")

		if err := c.SaveUploadedFile(file, tempInputPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded file"})
			return
		}

		// Cleanup temporary files after the request is handled
		defer os.Remove(tempInputPath)
		defer os.Remove(tempOutputPath)

		// Execute pdftotext utility
		// Command: pdftotext <input_pdf> <output_txt>
		cmd := exec.Command("pdftotext", tempInputPath, tempOutputPath)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Conversion failed: %v", err)})
			return
		}

		// Read the resulting text file
		content, err := os.ReadFile(tempOutputPath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read converted text"})
			return
		}

		// Return the content as plain text
		c.Header("Content-Type", "text/plain")
		c.String(http.StatusOK, string(content))
	})

	r.Run("0.0.0.0:5000")
}