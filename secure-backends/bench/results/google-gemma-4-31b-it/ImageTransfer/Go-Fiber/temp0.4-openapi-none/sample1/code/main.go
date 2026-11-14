package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

const (
	uploadDir = "./uploads"
	dbPath     = "./images.db"
)

type ImageMetadata struct {
	ID       string
	FilePath string
	MimeType string
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}

	statement := `CREATE TABLE IF NOT EXISTS images (
		id TEXT PRIMARY KEY, 
		path TEXT, 
		mime_type TEXT
	);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	// Ensure upload directory exists
	if _, err := os.Stat(uploadDir); os.IsNotExist(err) {
		_ = os.MkdirAll(uploadDir, 0755)
	}

	initDB()
	defer db.Close()

	app := fiber.New()

	// POST /upload
	app.Post("/upload", func(c *fiber.Ctx) error {
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Invalid input: file field is required",
			})
		}

		imageID := uuid.New().String()
		ext := filepath.Ext(file.Filename)
		savePath := filepath.Join(uploadDir, imageID+ext)

		// Save the file to disk
		if err := c.SaveFile(file, savePath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to save image",
			})
		}

		// Detect mime type based on file extension or content
		// Fiber's SaveFile doesn't provide mime, so we use http.DetectContentType on the saved file
		f, err := os.Open(savePath)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Internal server error"})
		}
		defer f.Close()

		buffer := make([]byte, 512)
		_, _ = f.Read(buffer)
		mimeType := http.DetectContentType(buffer)

		// Store metadata in SQLite
		_, err = db.Exec("INSERT INTO images (id, path, mime_type) VALUES (?, ?, ?)", imageID, savePath, mimeType)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to store image metadata",
			})
		}

		return c.Status(fiber.StatusOK).JSON(fiber.Map{
			"id": imageID,
		})
	})

	// GET /images/{imageId}
	app.Get("/images/:imageId", func(c *fiber.Ctx) error {
		imageID := c.Params("imageId")

		var meta ImageMetadata
		err := db.QueryRow("SELECT id, path, mime_type FROM images WHERE id = ?", imageID).Scan(&meta.ID, &meta.FilePath, &meta.MimeType)
		if err != nil {
			if err == sql.ErrNoRows {
				return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error": "Image not found",
				})
			}
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Internal server error",
			})
		}

		// Check if file exists on disk
		if _, err := os.Stat(meta.FilePath); os.IsNotExist(err) {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": "Image file missing from storage",
			})
		}

		// Set Content-Type to preserve original image format
		c.Set("Content-Type", meta.MimeType)
		
		// To ensure it's viewable in browser and not recommended for download:
		// 1. Content-Type is set to an image type.
		// 2. We avoid 'Content-Disposition: attachment'.
		// 3. We can set 'Content-Disposition: inline'.
		c.Set("Content-Disposition", "inline")

		return c.SendFile(meta.FilePath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}