package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

const (
	uploadDir = "./uploads"
	dbPath     = "./images.db"
	port      = "0.0.0.0:5000"
)

type ImageMetadata struct {
	ID          string
	ContentType string
	FilePath    string
}

type App struct {
	db *sql.DB
}

func main() {
	// Ensure upload directory exists
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		log.Fatal(err)
	}

	// Initialize SQLite database
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS images (
		id TEXT PRIMARY KEY,
		content_type TEXT,
		file_path TEXT
	)`)
	if err != nil {
		log.Fatal(err)
	}

	app := &App{db: db}

	mux := http.NewServeMux()
	mux.HandleFunc("/upload", app.handleUpload)
	mux.HandleFunc("/images/", app.handleGetImage)

	fmt.Printf("Server starting on %s\n", port)
	if err := http.ListenAndServe(port, mux); err != nil {
		log.Fatal(err)
	}
}

func (app *App) handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form (max 10MB)
	if err := r.ParseMultipartForm(10 << 20); err != nil {
		app.sendError(w, "Invalid input", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		app.sendError(w, "Missing file in request", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Generate unique ID and path
	id := uuid.New().String()
	ext := filepath.Ext(header.Filename)
	if ext == "" {
		ext = ".bin"
	}
	filePath := filepath.Join(uploadDir, id+ext)

	// Save file to disk
	dst, err := os.Create(filePath)
	if err != nil {
		app.sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		app.sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Save metadata to DB
	_, err = app.db.Exec("INSERT INTO images (id, content_type, file_path) VALUES (?, ?, ?)",
		id, header.Header.Get("Content-Type"), filePath)
	if err != nil {
		app.sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"id": id})
}

func (app *App) handleGetImage(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract imageId from path /images/{imageId}
	imageId := r.URL.Path[len("/images/"):]
	if imageId == "" {
		app.sendError(w, "Image ID required", http.StatusBadRequest)
		return
	}

	var meta ImageMetadata
	err := app.db.QueryRow("SELECT id, content_type, file_path FROM images WHERE id = ?", imageId).
		Scan(&meta.ID, &meta.ContentType, &meta.FilePath)

	if err == sql.ErrNoRows {
		app.sendError(w, "Image not found", http.StatusNotFound)
		return
	} else if err != nil {
		app.sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Open the file
	file, err := os.Open(meta.FilePath)
	if err != nil {
		app.sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer file.Close()

	// Set Content-Type to ensure browser renders it instead of downloading
	// If Content-Type is empty, we try to detect it via the file
	contentType := meta.ContentType
	if contentType == "" {
		contentType = http.DetectContentType([]byte("")) // Simplified, usually handled by ServeContent
	}

	w.Header().Set("Content-Type", contentType)
	// Content-Disposition: inline ensures it is viewable in browser
	w.Header().Set("Content-Disposition", "inline")

	if _, err := io.Copy(w, file); err != nil {
		// Header already sent, cannot send JSON error here
		log.Printf("Error streaming file: %v", err)
	}
}

func (app *App) sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": message})
}