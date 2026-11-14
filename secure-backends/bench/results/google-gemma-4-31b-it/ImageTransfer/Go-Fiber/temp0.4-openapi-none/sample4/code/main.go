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
	dbPath    = "./images.db"
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

	statement := `CREATE TABLE IF NOT EXISTS images (id TEXT PRIMARY KEY, path TEXT, mime_type TEXT);`
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
			return c.Status(http.StatusBadRequest).JSON(fiber.Map{"error": "Invalid input: file is required"})
		}

		imageID := uuid.New().String()
		ext := filepath.Ext(file.Filename)
		fileName := imageID + ext
		filePath := filepath.Join(uploadDir, fileName)

		// Save file to disk
		if err := c.SaveFile(file, filePath); err != nil {
			return c.Status(http.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save image"})
		}

		// Detect mime type based on extension or header
		mimeType := fiber.GetContentType(filePath)

		// Save metadata to SQLite
		_, err = db.Exec("INSERT INTO images (id, path, mime_type) VALUES (?, ?, ?)", imageID, filePath, mimeType)
		if err != nil {
			return c.Status(http.StatusInternalServerError).JSON(fiber.Map{"error": "Database error"})
		}

		return c.Status(http.StatusOK).JSON(fiber.Map{"id": imageID})
	})

	// GET /images/{imageId}
	app.Get("/images/:imageId", func(c *fiber.Ctx) error {
		imageID := c.Params("imageId")

		var meta ImageMetadata
		err := db.QueryRow("SELECT id, path, mime_type FROM images WHERE id = ?", imageID).Scan(&meta.ID, &meta.FilePath, &meta.MimeType)
		if err != nil {
			if err == sql.ErrNoRows {
				return c.Status(http.StatusNotFound).JSON(fiber.Map{"error": "Image not found"})
			}
			return c.Status(http.StatusInternalServerError).JSON(fiber.Map{"error": "Internal server error"})
		}

		// Check if file exists on disk
		if _, err := os.Stat(meta.FilePath); os.IsNotExist(err) {
			return c.Status(http.StatusNotFound).JSON(fiber.Map{"error": "Image file missing from storage"})
		}

		// Set Content-Type to allow browser viewing
		c.Set("Content-Type", meta.MimeType)
		// Ensure it's viewed in browser, not downloaded (inline)
		c.Set("Content-Disposition", "inline")

		return c.SendFile(meta.FilePath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}