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

	query := `CREATE TABLE IF NOT EXISTS images (
		id TEXT PRIMARY KEY,
		file_path TEXT,
		mime_type TEXT
	);`
	_, err = db.Exec(query)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	if _, err := os.Stat(uploadDir); os.IsNotExist(err) {
		os.MkdirAll(uploadDir, 0755)
	}

	app := fiber.New()

	app.Post("/upload", func(c *fiber.Ctx) error {
		file, err := c.FormFile("file")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid input: file is required"})
		}

		imageID := uuid.New().String()
		filename := fmt.Sprintf("%s%s", imageID, filepath.Ext(file.Filename))
		filePath := filepath.Join(uploadDir, filename)

		if err := c.SaveFileUpload(file, filePath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save file"})
		}

		// Detect mime type from the saved file
		mimeType := http.DetectContentType([]byte{}) // Default
		f, err := os.Open(filePath)
		if err == nil {
			buffer := make([]byte, 512)
			n, _ := f.Read(buffer)
			mimeType = http.DetectContentType(buffer[:n])
			f.Close()
		}

		_, err = db.Exec("INSERT INTO images (id, file_path, mime_type) VALUES (?, ?, ?)", imageID, filePath, mimeType)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Database error"})
		}

		return c.Status(fiber.StatusOK).JSON(fiber.Map{"id": imageID})
	})

	app.Get("/images/:imageId", func(c *fiber.Ctx) error {
		imageID := c.Params("imageId")

		var meta ImageMetadata
		err := db.QueryRow("SELECT id, file_path, mime_type FROM images WHERE id = ?", imageID).Scan(&meta.ID, &meta.FilePath, &meta.MimeType)
		if err == sql.ErrNoRows {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Image not found"})
		} else if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Internal server error"})
		}

		if _, err := os.Stat(meta.FilePath); os.IsNotExist(err) {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Image file missing on disk"})
		}

		// Set Content-Type to ensure browser renders it and not downloads it
		c.Set("Content-Type", meta.MimeType)
		// Ensure Content-Disposition is not set to attachment
		c.Set("Content-Disposition", "inline")

		return c.SendFile(meta.FilePath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}