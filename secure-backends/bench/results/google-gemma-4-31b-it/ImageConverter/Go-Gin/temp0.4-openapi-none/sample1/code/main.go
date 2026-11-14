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
			c.JSON(http.StatusBadRequest, gin.H{"error": "images are required"})
			return
		}

		// Get targetSize
		targetSize := c.PostForm("targetSize")
		if targetSize == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "targetSize is required"})
			return
		}

		// Get delay (default 10)
		delayStr := c.PostForm("delay")
		delay := 10
		if delayStr != "" {
			if d, err := strconv.Atoi(delayStr); err == nil {
				delay = d
			}
		}

		// Get appendReverted (default false)
		appendRevertedStr := c.PostForm("appendReverted")
		appendReverted := false
		if appendRevertedStr == "true" {
			appendReverted = true
		}

		// Create temporary directory for processing
		tempDir, err := os.MkdirTemp("", "gif-creator-")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create temp directory"})
			return
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, file := range files {
			path := filepath.Join(tempDir, fmt.Sprintf("img_%d", i))
			if err := c.SaveUploadedFile(file, path); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded file"})
				return
			}
			inputPaths = append(inputPaths, path)
		}

		// Handle appendReverted: add paths in reverse order
		if appendReverted {
			for i := len(inputPaths) - 1; i >= 0; i-- {
				inputPaths = append(inputPaths, inputPaths[i])
			}
		}

		// Output path
		outputFile := filepath.Join(tempDir, uuid.New().String()+".gif")

		// Build ImageMagick command: convert -delay <ms/10> -size <WxH> <files...> <output>
		// Note: ImageMagick -delay is in ticks (usually 1/100th of a second). 
		// To get milliseconds, we divide by 10.
		delayTicks := delay / 10
		
		args := []string{}
		args = append(args, "-delay", strconv.Itoa(delayTicks))
		args = append(args, "-resize", targetSize)
		args = append(args, inputPaths...)
		args = append(args, outputFile)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "ImageMagick conversion failed: " + err.Error()})
			return
		}

		// Serve the resulting GIF
		c.Header("Content-Type", "image/gif")
		c.File(outputFile)
	})

	r.Run("0.0.0.0:5000")
}