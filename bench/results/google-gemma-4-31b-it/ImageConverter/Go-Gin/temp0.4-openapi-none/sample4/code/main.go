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
			c.JSON(http.StatusBadRequest, gin.H{"error": "No images provided"})
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
		appendReverted := c.PostForm("appendReverted") == "true"

		// Create a temporary directory for processing
		tempDir, err := os.MkdirTemp("", "gif-creator-")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create temp directory"})
			return
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, file := range files {
			path := filepath.Join(tempDir, fmt.Sprintf("img_%d%s", i, filepath.Ext(file.Filename)))
			if err := c.SaveUploadedFile(file, path); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded file"})
				return
			}
			inputPaths = append(inputPaths, path)
		}

		// Handle appendReverted: duplicate images in reverse order
		if appendReverted {
			for i := len(inputPaths) - 1; i >= 0; i-- {
				revPath := filepath.Join(tempDir, fmt.Sprintf("rev_%d%s", i, filepath.Ext(inputPaths[i])))
				// Copy file to new path to ensure ImageMagick treats them as separate frames
				inputData, err := os.ReadFile(inputPaths[i])
				if err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to process reverted images"})
					return
				}
				if err := os.WriteFile(revPath, inputData, 0644); err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to process reverted images"})
					return
				}
				inputPaths = append(inputPaths, revPath)
			}
		}

		// Output filename
		outputFilename := uuid.New().String() + ".gif"
		outputPath := filepath.Join(tempDir, outputFilename)

		// Build ImageMagick command
		// -delay is in ticks (1/100th of a second), so we divide ms by 10
		delayTicks := strconv.Itoa(delay / 10)
		
		args := []string{"convert", "-delay", delayTicks}
		args = append(args, inputPaths...)
		args = append(args, "-resize", targetSize)
		args = append(args, outputPath)

		cmd := exec.Command("convert", args[1:]...)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "ImageMagick conversion failed: " + err.Error()})
			return
		}

		// Serve the resulting GIF
		c.File(outputPath)
	})

	r.Run("0.0.0.0:5000")
}