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
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
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
		imageID := uuid.New().String()
		
		// Preserve original extension
		ext := filepath.Ext(file.Filename)
		filename := imageID + ext
		savePath := filepath.Join(uploadDir, filename)

		// Save the file to the filesystem
		if err := c.SaveUploadedFile(file, savePath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save image"})
			return
		}

		// Store the mapping of ID to filename in a way we can retrieve it.
		// For this implementation, we use the ID as the filename base.
		c.JSON(http.StatusOK, gin.H{"id": imageID})
	})

	// GET /images/{imageId} - Share/View an image
	r.GET("/images/:imageId", func(c *gin.Context) {
		imageID := c.Param("imageId")
		
		// Search for the file starting with the imageID in the upload directory
		files, err := os.ReadDir(uploadDir)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}

		var foundFile string
		for _, f := range files {
			// Check if the filename starts with the imageID (ignoring extension)
			if len(f.Name()) >= len(imageID) && f.Name()[:len(imageID)] == imageID {
				foundFile = f.Name()
				break
			}
		}

		if foundFile == "" {
			c.JSON(http.StatusNotFound, gin.H{"error": "Image not found"})
			return
		}

		filePath := filepath.Join(uploadDir, foundFile)
		
		// To ensure the image is viewable in the browser and not downloaded:
		// 1. We use c.File() which automatically detects Content-Type based on extension.
		// 2. We avoid setting "Content-Disposition: attachment".
		// Gin's c.File() sets "Content-Type" and "Content-Length" correctly.
		c.File(filePath)
	})

	// Start server on 0.0.0.0:5000
	fmt.Println("Server starting on 0.0.0.0:5000")
	if err := r.Run("0.0.0.0:5000"); err != nil {
		log.Fatal("ListenAndServe: ", err)
	}
}