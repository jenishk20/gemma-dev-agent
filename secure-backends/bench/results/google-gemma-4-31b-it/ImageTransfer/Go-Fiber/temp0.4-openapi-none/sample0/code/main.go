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

type ImageRecord struct {
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
		os.MkdirAll(uploadDir, 0755)
	}

	initDB()
	defer db.Close()

	app := fiber.New()

	// POST /upload
	app.Post("/upload", func(c *fiber.Ctx) error {
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid input: file field is required"})
		}

		imageID := uuid.New().String()
		filePath := filepath.Join(uploadDir, imageID+filepath.Ext(file.Filename))

		// Save file to disk
		if err := c.SaveFile(file, filePath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save image"})
		}

		// Determine MIME type
		mimeType := http.DetectContentType([]byte(file.Filename)) // Simplified; Fiber doesn't provide raw bytes easily without reading
		// Better way: read first 512 bytes
		f, err := os.Open(filePath)
		if err == nil {
			buffer := make([]byte, 512)
			n, _ := f.Read(buffer)
			f.Close()
			mimeType = http.DetectContentType(buffer[:n])
		}

		// Save to DB
		_, err = db.Exec("INSERT INTO images (id, path, mime_type) VALUES (?, ?, ?)", imageID, filePath, mimeType)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Database error"})
		}

		return c.Status(fiber.StatusOK).JSON(fiber.Map{"id": imageID})
	})

	// GET /images/{imageId}
	app.Get("/images/:imageId", func(c *fiber.Ctx) error {
		imageID := c.Params("imageId")

		var record ImageRecord
		err := db.QueryRow("SELECT id, path, mime_type FROM images WHERE id = ?", imageID).Scan(&record.ID, &record.FilePath, &record.MimeType)
		if err == sql.ErrNoRows {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Image not found"})
		} else if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Database error"})
		}

		// Check if file exists on disk
		if _, err := os.Stat(record.FilePath); os.IsNotExist(err) {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Image file missing from storage"})
		}

		// Set Content-Type to preserve original format and ensure browser displays it
		c.Set("Content-Type", record.MimeType)
		// Ensure it's viewed in browser (inline) and not forced download
		c.Set("Content-Disposition", "inline")

		return c.SendFile(record.FilePath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}