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
		log.Fatal("Could not create upload directory:", err)
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
		
		// Preserve original extension
		ext := filepath.Ext(file.Filename)
		filename := id + ext
		savePath := filepath.Join(uploadDir, filename)

		// Save the file to disk
		if err := c.SaveUploadedFile(file, savePath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save image"})
			return
		}

		// Store the mapping of ID to actual filename in a way we can retrieve it.
		// For this implementation, we store the filename as the ID in the path 
		// but the OpenAPI requires returning the ID. 
		// We will use the UUID as the ID and store the extension in a simple map or just use the UUID as the filename.
		// To keep it simple and robust, we'll store the full filename (with ext) as the "id" 
		// or manage a small metadata store. Let's use the UUID as the ID and store the filename.
		
		// Since we need to retrieve by ID, and the ID is the UUID, 
		// we will store the file as UUID.bin and keep track of the content type.
		// However, the simplest way to satisfy "preserve mimetype" and "view in browser" 
		// is to save the file with its extension and return the UUID.
		
		// Let's refine: we save the file as <uuid><ext> and return the <uuid><ext> as the ID.
		c.JSON(http.StatusOK, gin.H{"id": filename})
	})

	// GET /images/{imageId} - Share an image
	r.GET("/images/:imageId", func(c *gin.Context) {
		imageId := c.Param("imageId")
		filePath := filepath.Join(uploadDir, imageId)

		// Check if file exists
		if _, err := os.Stat(filePath); os.IsNotExist(err) {
			c.JSON(http.StatusNotFound, gin.H{"error": "Image not found"})
			return
		}

		// To ensure it is viewable in browser and not recommended for download:
		// 1. We use c.File which sets the Content-Type based on extension.
		// 2. We ensure Content-Disposition is not 'attachment'.
		
		// Gin's c.File sets the Content-Type automatically.
		// To prevent download, we ensure we don't set Content-Disposition to attachment.
		// By default, c.File provides an inline response.
		c.File(filePath)
	})

	fmt.Println("Server starting on 0.0.0.0:5000")
	r.Run("0.0.0.0:5000")
}