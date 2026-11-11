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
	dbFile    = "./images.db"
)

type ImageMetadata struct {
	ID       string
	FilePath string
	MimeType string
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", dbFile)
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS images (
		id TEXT PRIMARY KEY,
		file_path TEXT,
		mime_type TEXT
	);`
	_, err = db.Exec(sqlStmt)
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

		// Save file to disk
		if err := c.SaveFile(file, savePath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to save image",
			})
		}

		// Detect mime type based on extension or use Fiber's helper
		// For simplicity and reliability, we'll use the standard library's detection via the file header
		mimeType := http.DetectContentType([]byte{}) // Placeholder, we'll get it from the file
		
		// Re-open file to detect actual content type
		f, err := os.Open(savePath)
		if err == nil {
			buffer := make([]byte, 512)
			_, _ = f.Read(buffer)
			mimeType = http.DetectContentType(buffer)
			f.Close()
		}

		_, err = db.Exec("INSERT INTO images (id, file_path, mime_type) VALUES (?, ?, ?)", imageID, savePath, mimeType)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Database error",
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
		err := db.QueryRow("SELECT id, file_path, mime_type FROM images WHERE id = ?", imageID).Scan(&meta.ID, &meta.FilePath, &meta.MimeType)
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

		// To ensure it is viewable in browser and not downloaded:
		// 1. Set Content-Type to the original mime type
		// 2. Set Content-Disposition to inline
		c.Set("Content-Type", meta.MimeType)
		c.Set("Content-Disposition", "inline")

		return c.SendFile(meta.FilePath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}