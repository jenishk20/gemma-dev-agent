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
		// Parse multipart form fields
		videoFile, err := c.FormFile("video")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Video file is required"})
			return
		}

		frameNumberStr := c.PostForm("frameNumber")
		if frameNumberStr == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "frameNumber is required"})
			return
		}

		frameNumber, err := strconv.Atoi(frameNumberStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "frameNumber must be an integer"})
			return
		}

		// Create unique directory for this request to avoid collisions
		requestID := uuid.New().String()
		tmpDir := filepath.Join(os.TempDir(), requestID)
		if err := os.MkdirAll(tmpDir, 0755); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}
		defer os.RemoveAll(tmpDir)

		// Save uploaded video
		videoPath := filepath.Join(tmpDir, "input_video")
		if err := c.SaveUploadedFile(videoFile, videoPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded video"})
			return
		}

		// Output path for the extracted frame
		outputPath := filepath.Join(tmpDir, "frame.png")

		// FFmpeg command to extract a specific frame
		// -i: input file
		// -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
		// -vframes 1: output exactly one frame
		cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n\\,%d)", frameNumber), "-vframes", "1", outputPath)
		
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber)})
			return
		}

		// Check if the output file was actually created
		if _, err := os.Stat(outputPath); os.IsNotExist(err) {
			c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber)})
			return
		}

		// Serve the image
		c.File(outputPath)
	})

	r.Run("0.0.0.0:5000")
}