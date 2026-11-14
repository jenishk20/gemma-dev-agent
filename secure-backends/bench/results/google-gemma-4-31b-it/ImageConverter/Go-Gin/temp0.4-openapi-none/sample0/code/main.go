package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func main() {
	r := gin.Default()

	r.POST("/create-gif", func(c *gin.Context) {
		// Parse multipart form
		form, err := c.MultipartForm()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid multipart form"})
			return
		}

		// Get images
		files := form.File["images"]
		if len(files) == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "images field is required"})
			return
		}

		// Get targetSize
		targetSize := c.PostForm("targetSize")
		if targetSize == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "targetSize is required"})
			return
		}

		// Get delay
		delayStr := c.DefaultPostForm("delay", "10")
		delay, err := strconv.Atoi(delayStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "delay must be an integer"})
			return
		}

		// Get appendReverted
		appendRevertedStr := c.DefaultPostForm("appendReverted", "false")
		appendReverted, err := strconv.ParseBool(appendRevertedStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "appendReverted must be a boolean"})
			return
		}

		// Create temporary directory for processing
		tempDir, err := os.MkdirTemp("", "gif-creator-")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create temp directory"})
			return
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			filePath := filepath.Join(tempDir, fmt.Sprintf("img_%d_%s", i, fileHeader.Filename))
			if err := c.SaveUploadedFile(fileHeader, filePath); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded image"})
				return
			}
			inputPaths = append(inputPaths, filePath)
		}

		// Handle appendReverted logic
		var finalInputPaths []string
		finalInputPaths = append(finalInputPaths, inputPaths...)
		if appendReverted {
			for i := len(inputPaths) - 1; i >= 0; i-- {
				finalInputPaths = append(finalInputPaths, inputPaths[i])
			}
		}

		// Output filename
		outputFileName := uuid.New().String() + ".gif"
		outputPath := filepath.Join(tempDir, outputFileName)

		// ImageMagick command construction
		// convert -delay <delay> -resize <size> <inputs> <output>
		// Note: ImageMagick delay is in 1/100ths of a second. 
		// The API specifies milliseconds. So we divide by 10.
		imDelay := fmt.Sprintf("%d", delay/10)
		
		args := []string{}
		args = append(args, "-delay", imDelay)
		args = append(args, "-resize", targetSize)
		args = append(args, finalInputPaths...)
		args = append(args, outputPath)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "ImageMagick conversion failed: " + err.Error()})
			return
		}

		// Serve the resulting GIF
		c.Header("Content-Type", "image/gif")
		if err := c.File(outputPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to serve generated GIF"})
			return
		}
	})

	r.Run("0.0.0.0:5000")
}