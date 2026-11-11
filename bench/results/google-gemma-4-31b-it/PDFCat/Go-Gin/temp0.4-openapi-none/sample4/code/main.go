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

		// Create a unique temporary directory for this request to avoid collisions
		requestID := uuid.New().String()
		tempDir, err := os.MkdirTemp("", "pdfconcat-"+requestID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "An error occurred while processing the files."})
			return
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			filePath := filepath.Join(tempDir, fmt.Sprintf("input_%d.pdf", i))
			if err := c.SaveUploadedFile(fileHeader, filePath); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "An error occurred while processing the files."})
				return
			}
			inputPaths = append(inputPaths, filePath)
		}

		outputFile := filepath.Join(tempDir, "output.pdf")

		// Construct pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
		args := append(inputPaths, outputFile)
		cmd := exec.Command("pdfunite", args...)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "An error occurred while processing the files."})
			return
		}

		// Serve the resulting PDF
		c.FileAttachment(outputFile, "concatenated.pdf")
	})

	r.Run("0.0.0.0:5000")
}