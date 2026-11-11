package main

import (
	"net/http"
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
		// filepath.Base ensures we only get the filename, not a path
		safeFilename := filepath.Base(req.Filename)
		fullPath := filepath.Join(songsDirectory, safeFilename)

		// Check if the file exists and is accessible
		// Gin's File method handles the streaming and content-type detection
		// We explicitly set the content type to audio/mpeg as per OpenAPI spec
		c.Header("Content-Type", "audio/mpeg")
		
		// Use File method which efficiently streams the file from disk
		// If the file doesn't exist, Gin will automatically send a 404
		c.File(fullPath)
	})

	r.Run("0.0.0.0:5000")
}