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
		// Parse targetSize
		targetSize := c.PostForm("targetSize")
		if targetSize == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "targetSize is required"})
			return
		}

		// Parse delay
		delayStr := c.DefaultPostForm("delay", "10")
		delay, err := strconv.Atoi(delayStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "delay must be an integer"})
			return
		}

		// Parse appendReverted
		appendRevertedStr := c.DefaultPostForm("appendReverted", "false")
		appendReverted, err := strconv.ParseBool(appendRevertedStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "appendReverted must be a boolean"})
			return
		}

		// Handle images
		form, err := c.MultipartForm()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "failed to parse multipart form"})
			return
		}

		files := form.File["images"]
		if len(files) == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "at least one image is required"})
			return
		}

		// Create a temporary directory for processing
		tempDir, err := os.MkdirTemp("", "gif-creator-")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create temp directory"})
			return
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			filePath := filepath.Join(tempDir, fmt.Sprintf("img_%d%s", i, filepath.Ext(fileHeader.Filename)))
			if err := c.SaveUploadedFile(fileHeader, filePath); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to save uploaded image"})
				return
			}
			inputPaths = append(inputPaths, filePath)
		}

		// If appendReverted is true, add the images in reverse order
		if appendReverted {
			for i := len(inputPaths) - 1; i >= 0; i-- {
				inputPaths = append(inputPaths, inputPaths[i])
			}
		}

		// Output file path
		outputFileName := uuid.New().String() + ".gif"
		outputPath := filepath.Join(tempDir, outputFileName)

		// Construct ImageMagick command: convert -delay <ms/10> -size <WxH> <files> <output>
		// ImageMagick delay is in ticks (1/100th of a second), so ms / 10
		delayTicks := strconv.Itoa(delay / 10)
		
		args := []string{}
		args = append(args, "-delay", delayTicks)
		args = append(args, "-resize", targetSize)
		args = append(args, inputPaths...)
		args = append(args, outputPath)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "ImageMagick conversion failed: " + err.Error()})
			return
		}

		// Serve the resulting GIF
		c.Header("Content-Type", "image/gif")
		c.File(outputPath)
	})

	r.Run("0.0.0.0:5000")
}