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

		// Prevent directory traversal attacks by cleaning the path and ensuring it's just a filename
		safeFilename := filepath.Base(req.Filename)
		filePath := filepath.Join(songsDirectory, safeFilename)

		// Check if file exists and is not a directory
		info, err := os.Stat(filePath)
		if os.IsNotExist(err) || info.IsDir() {
			c.JSON(http.StatusNotFound, gin.H{"error": "File does not exist"})
			return
		}

		// Set the content type to audio/mpeg as per OpenAPI spec
		c.Header("Content-Type", "audio/mpeg")
		
		// Stream the file to the client
		c.File(filePath)
	})

	r.Run("0.0.0.0:5000")
}