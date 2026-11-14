package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

const uploadDir = "./uploads"

func main() {
	// Ensure upload directory exists
	if err := os.MkdirAll(uploadDir, os.ModePerm); err != nil {
		log.Fatal("Failed to create upload directory:", err)
	}

	r := gin.Default()

	// POST /upload
	r.POST("/upload", func(c *gin.Context) {
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input: file field is required"})
			return
		}

		// Generate a unique ID for the image
		id := uuid.New().String()
		
		// Preserve original extension
		ext := filepath.Ext(file.Filename)
		filename := id + ext
		dst := filepath.Join(uploadDir, filename)

		// Save the file to disk
		if err := c.SaveUploadedFile(file, dst); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save image"})
			return
		}

		// Store the mapping of ID to filename in a way we can retrieve it
		// For this simple implementation, we store the ID as the filename (minus extension)
		// and use the filesystem as the source of truth.
		// We save the full filename in a simple map or just derive it.
		// To strictly follow the schema returning 'id', we return the UUID.
		
		// We need to store the extension to retrieve the file later.
		// We'll save a small metadata file or just use the ID as the base.
		// Let's save the extension in a simple way: filename is id + ext.
		// We'll store the mapping in a global map for this exercise.
		imageMap[id] = filename

		c.JSON(http.StatusOK, gin.H{"id": id})
	})

	// GET /images/{imageId}
	r.GET("/images/:imageId", func(c *gin.Context) {
		imageId := c.Param("imageId")
		filename, exists := imageMap[imageId]
		if !exists {
			c.JSON(http.StatusNotFound, gin.H{"error": "Image not found"})
			return
		}

		filePath := filepath.Join(uploadDir, filename)
		
		// Check if file exists on disk
		if _, err := os.Stat(filePath); os.IsNotExist(err) {
			c.JSON(http.StatusNotFound, gin.H{"error": "Image not found on disk"})
			return
		}

		// To ensure the image is viewable in the browser and not downloaded:
		// 1. We use c.File() which sets the Content-Type based on extension.
		// 2. We ensure Content-Disposition is not set to 'attachment'.
		// Gin's c.File() handles the Content-Type automatically via the mime package.
		c.Header("Content-Disposition", "inline")
		c.File(filePath)
	})

	fmt.Println("Server starting on 0.0.0.0:5000")
	r.Run("0.0.0.0:5000")
}

var imageMap = make(map[string]string)