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

		// Prevent directory traversal attacks by taking only the base filename
		safeFilename := filepath.Base(req.Filename)
		fullPath := filepath.Join(songsDirectory, safeFilename)

		// Check if file exists and is accessible
		if _, err := os.Stat(fullPath); os.IsNotExist(err) {
			c.JSON(http.StatusNotFound, gin.H{"error": "File does not exist"})
			return
		}

		// Set the content type to audio/mpeg as per OpenAPI spec
		c.Header("Content-Type", "audio/mpeg")
		
		// Stream the file to the client
		c.File(fullPath)
	})

	r.Run("0.0.0.0:5000")
}