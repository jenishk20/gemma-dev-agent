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
			c.JSON(http.StatusBadRequest, gin.H{"error": "No file uploaded or invalid request"})
			return
		}

		// Generate a unique ID for the image
		id := uuid.New().String()
		
		// Preserve original extension
		ext := filepath.Ext(file.Filename)
		filename := id + ext
		savePath := filepath.Join(uploadDir, filename)

		// Save the file to disk
		if err := c.SaveUploadedFile(file, savePath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save image"})
			return
		}

		// Store the mapping of ID to filename in a way we can retrieve it.
		// For this implementation, we use the ID as the base filename.
		// We save the original extension in the filename itself.
		// To retrieve it, we look for any file starting with the ID.
		c.JSON(http.StatusOK, gin.H{"id": id})
	})

	// GET /images/{imageId} - Share/View an image
	r.GET("/images/:imageId", func(c *gin.Context) {
		imageId := c.Param("imageId")

		// Find the file that starts with the imageId in the upload directory
		files, err := os.ReadDir(uploadDir)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}

		var targetFile string
		for _, f := range files {
			if len(f.Name()) > len(imageId) && f.Name()[:len(imageId)] == imageId {
				targetFile = f.Name()
				break
			}
		}

		if targetFile == "" {
			c.JSON(http.StatusNotFound, gin.H{"error": "Image not found"})
			return
		}

		fullPath := filepath.Join(uploadDir, targetFile)
		
		// To ensure it is viewable in browser and not downloaded:
		// 1. Gin's File method automatically detects Content-Type based on extension.
		// 2. We set Content-Disposition to inline.
		c.Header("Content-Disposition", "inline")
		
		// Serve the file
		http.ServeFile(c.Writer, c.Request, fullPath)
	})

	// Start server on 0.0.0.0:5000
	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := r.Run("0.0.0.0:5000"); err != nil {
		log.Fatal("Server failed to start:", err)
	}
}