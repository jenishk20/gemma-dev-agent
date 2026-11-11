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

	// POST /upload - Upload an image
	r.POST("/upload", func(c *gin.Context) {
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input: file field is required"})
			return
		}

		// Generate a unique ID for the image
		id := uuid.New().String()
		
		// Preserve the original extension to help with MIME type detection
		ext := filepath.Ext(file.Filename)
		filename := id + ext
		savePath := filepath.Join(uploadDir, filename)

		// Save the file to the local filesystem
		if err := c.SaveUploadedFile(file, savePath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save image"})
			return
		}

		// Store the mapping of ID to filename in a way that we can retrieve it.
		// For this implementation, we use a simple naming convention where ID is the filename base.
		// We store the actual filename (including extension) in a simple map or just derive it.
		// To keep it simple and stateless for this single-file requirement, 
		// we'll store the extension in a small metadata file or just search for the file.
		// However, since we need to return the ID, we can just store the full filename as the ID 
		// or manage a map. Let's use a global map for simplicity.
		imageMap[id] = filename

		c.JSON(http.StatusOK, gin.H{"id": id})
	})

	// GET /images/{imageId} - Share/View an image
	r.GET("/images/:imageId", func(c *gin.Context) {
		imageId := c.Param("imageId")
		filename, exists := imageMap[imageId]
		if !exists {
			c.JSON(http.StatusNotFound, gin.H{"error": "Image not found"})
			return
		}

		filePath := filepath.Join(uploadDir, filename)
		
		// Check if file actually exists on disk
		if _, err := os.Stat(filePath); os.IsNotExist(err) {
			c.JSON(http.StatusNotFound, gin.H{"error": "Image file missing from storage"})
			return
		}

		// ServeFile automatically detects the Content-Type based on the extension.
		// To ensure it is viewable in the browser and not downloaded, 
		// Gin/net/http sets Content-Disposition to inline by default for known image types.
		c.Header("Content-Disposition", "inline")
		c.File(filePath)
	})

	// Start server on 0.0.0.0:5000
	fmt.Println("Server starting on 0.0.0.0:5000")
	if err := r.Run("0.0.0.0:5000"); err != nil {
		log.Fatal("Server failed to start:", err)
	}
}

// imageMap stores the mapping from the UUID to the actual filename on disk
var imageMap = make(map[string]string)