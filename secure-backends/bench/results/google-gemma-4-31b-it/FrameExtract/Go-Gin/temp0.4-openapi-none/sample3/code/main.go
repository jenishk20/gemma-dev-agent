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
		// -vf: video filter "select=eq(n,X)" selects the frame at index X
		// -vframes 1: output exactly one frame
		// -f image2: force image format
		cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n,%d)", frameNumber), "-vframes", "1", "-f", "image2", outputPath)
		
		if err := cmd.Run(); err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber)})
			return
		}

		// 4. Serve the extracted image
		imageFile, err := os.Open(outputPath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read extracted frame"})
			return
		}
		defer imageFile.Close()

		c.Header("Content-Type", "image/png")
		c.Header("Content-Disposition", "attachment; filename=frame.png")
		
		// Stream the file back to the client
		_, err = c.Writer.Write(func() []byte {
			data, _ := os.ReadFile(outputPath)
			return data
		}())
		
		// Note: Gin's FileData or File is cleaner, but for simplicity in one file:
		// Using c.File is the standard Gin way to send a file.
		// However, since we already opened it, we'll use c.File for reliability.
	})

	// Overriding the handler slightly to use c.File for the response
	r.POST("/extract", func(c *gin.Context) {
		frameNumberStr := c.PostForm("frameNumber")
		frameNumber, err := strconv.Atoi(frameNumberStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid frameNumber"})
			return
		}

		file, err := c.FormFile("video")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Video file is required"})
			return
		}

		requestID := uuid.New().String()
		tempDir := os.TempDir()
		videoPath := filepath.Join(tempDir, requestID+"_"+file.Filename)
		outputPath := filepath.Join(tempDir, requestID+"_frame.png")

		if err := c.SaveUploadedFile(file, videoPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save uploaded video"})
			return
		}

		// We can't use defer os.Remove(outputPath) here because c.File is asynchronous/streaming
		// Instead, we use a custom response writer or just accept that we'll clean up manually
		// But for this exercise, we will read the file into memory and then delete.
		
		cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n,%d)", frameNumber), "-vframes", "1", "-f", "image2", outputPath)
		
		if err := cmd.Run(); err != nil {
			os.Remove(videoPath)
			c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber)})
			return
		}

		data, err := os.ReadFile(outputPath)
		os.Remove(videoPath)
		os.Remove(outputPath)

		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read extracted frame"})
			return
		}

		c.Data(http.StatusOK, "image/png", data)
	})

	r.Run("0.0.0.0:5000")
}