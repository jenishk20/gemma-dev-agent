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

	r.POST("/extract", func(c *gin.Context) {
		// 1. Parse request parameters
		frameNumberStr := c.PostForm("frameNumber")
		frameNumber, err := strconv.Atoi(frameNumberStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid frameNumber"})
			return
		}

		// 2. Handle video file upload
		file, err := c.FormFile("video")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Video file is required"})
			return
		}

		// Create a unique directory for this request to avoid collisions
		requestID := uuid.New().String()
		tempDir := filepath.Join(os.TempDir(), requestID)
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}
		defer os.RemoveAll(tempDir)

		videoPath := filepath.Join(tempDir, file.Filename)
		if err := c.SaveUploadedFile(file, videoPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded video"})
			return
		}

		// 3. Use ffmpeg to extract the specific frame
		// -i: input file
		// -vf: video filter "select=eq(n\,FRAME_INDEX)" selects the specific frame
		// -vframes 1: output exactly one frame
		// -f image2: output format as image
		outputImage := filepath.Join(tempDir, "frame.png")
		cmd := exec.Command("ffmpeg",
			"-i", videoPath,
			"-vf", fmt.Sprintf("select=eq(n,%d)", frameNumber),
			"-vframes", "1",
			"-f", "image2",
			outputImage,
		)

		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber)})
			return
		}

		// 4. Serve the extracted image
		c.File(outputImage)
	})

	r.Run("0.0.0.0:5000")
}