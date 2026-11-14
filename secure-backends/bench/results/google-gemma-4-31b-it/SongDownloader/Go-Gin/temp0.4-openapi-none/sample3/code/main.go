package main

import (
	"net/http"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
)

const songsDirectory = "/var/songs"

type DownloadRequest struct {
	Filename string `json:"filename" binding:"required"`
}

func main() {
	r := gin.Default()

	r.POST("/download", func(c *gin.Context) {
		var req DownloadRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		// Sanitize filename to prevent directory traversal attacks
		safeFilename := filepath.Base(req.Filename)
		if safeFilename == "." || safeFilename == "/" || safeFilename != req.Filename {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid filename"})
			return
		}

		filePath := filepath.Join(songsDirectory, safeFilename)

		// Check if file exists and is a regular file
		fileInfo, err := os.Stat(filePath)
		if os.IsNotExist(err) || fileInfo.IsDir() {
			c.JSON(http.StatusNotFound, gin.H{"error": "File does not exist"})
			return
		}

		// Set headers for audio streaming
		c.Header("Content-Type", "audio/mpeg")
		c.Header("Content-Disposition", "attachment; filename="+safeFilename)
		c.Header("Content-Length", string(rune(fileInfo.Size())))

		// Stream the file to the client
		c.File(filePath)
	})

	r.Run("0.0.0.0:5000")
}