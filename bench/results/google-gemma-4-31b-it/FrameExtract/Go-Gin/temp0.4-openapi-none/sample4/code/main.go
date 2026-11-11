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
		// 1. Parse form fields
		frameNumberStr := c.PostForm("frameNumber")
		frameNumber, err := strconv.Atoi(frameNumberStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid frameNumber"})
			return
		}

		// 2. Handle video upload
		file, err := c.FormFile("video")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Video file is required"})
			return
		}

		// Create unique IDs for temporary files to avoid collisions
		requestID := uuid.New().String()
		tempDir := os.TempDir()
		videoPath := filepath.Join(tempDir, requestID+"_"+file.Filename)
		outputPath := filepath.Join(tempDir, requestID+"_frame.png")

		// Save uploaded file to disk
		if err := c.SaveUploadedFile(file, videoPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded video"})
			return
		}

		// Cleanup files after request
		defer os.Remove(videoPath)
		defer os.Remove(outputPath)

		// 3. Execute ffmpeg command
		// -i: input file
		// -vf "select=eq(n,FRAME_INDEX)": select the specific frame index
		// -vframes 1: output exactly one frame
		// -f image2: force image format
		cmd := exec.Command("ffmpeg",
			"-i", videoPath,
			"-vf", fmt.Sprintf("select=eq(n,%d)", frameNumber),
			"-vframes", "1",
			"-f", "image2",
			outputPath,
		)

		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber)})
			return
		}

		// 4. Serve the resulting image
		c.Header("Content-Type", "image/png")
		c.File(outputPath)
	})

	r.Run("0.0.0.0:5000")
}