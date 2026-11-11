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

	r.POST("/concatenate", func(c *gin.Context) {
		// Get files from multipart form
		form, err := c.MultipartForm()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input or missing files."})
			return
		}

		files := form.File["files"]
		if len(files) == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input or missing files."})
			return
		}

		// Create a temporary directory for this request to avoid collisions
		tempDir, err := os.MkdirTemp("", "pdfconcat-*")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "An error occurred while processing the files."})
			return
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			// Create a unique filename for each uploaded part
			filePath := filepath.Join(tempDir, fmt.Sprintf("input_%d_%s.pdf", i, fileHeader.Filename))
			
			// Save the uploaded file to the temp directory
			if err := c.SaveUploadedFile(fileHeader, filePath); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "An error occurred while processing the files."})
				return
			}
			inputPaths = append(inputPaths, filePath)
		}

		// Define output path
		outputFileName := uuid.New().String() + ".pdf"
		outputPath := filepath.Join(tempDir, outputFileName)

		// Build the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
		args := append(inputPaths, outputPath)
		cmd := exec.Command("pdfunite", args...)

		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "An error occurred while processing the files."})
			return
		}

		// Serve the resulting PDF file
		c.File(outputPath)
	})

	r.Run("0.0.0.0:5000")
}