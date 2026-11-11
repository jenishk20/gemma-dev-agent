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

type ImageMetadata struct {
	ID          string
	ContentType string
	FilePath    string
}

var db *sql.DB
var uploadDir = "./uploads"

func main() {
	// Ensure upload directory exists
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		log.Fatal(err)
	}

	// Initialize SQLite database
	var err error
	db, err = sql.Open("sqlite3", "./images.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table for image metadata
	statement := `CREATE TABLE IF NOT EXISTS images (id TEXT PRIMARY KEY, content_type TEXT, path TEXT);`
	if _, err := db.Exec(statement); err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/upload", handleUpload)
	mux.HandleFunc("/images/", handleGetImage)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", mux); err != nil {
		log.Fatal(err)
	}
}

func handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Limit upload size to 10MB
	r.Body = http.MaxBytesReader(w, r.Body, 10<<20)

	// Parse multipart form
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		sendError(w, "Invalid input", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		sendError(w, "File is required", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Generate unique ID and filename
	id := uuid.New().String()
	ext := filepath.Ext(header.Filename)
	filePath := filepath.Join(uploadDir, id+ext)

	// Save file to disk
	dst, err := os.Create(filePath)
	if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Store metadata in DB
	contentType := http.DetectContentType(nil) // Placeholder, we'll get it from the file
	// To get actual content type, we read the first 512 bytes
	f, _ := os.Open(filePath)
	buf := make([]byte, 512)
	n, _ := f.Read(buf)
	f.Close()
	contentType = http.DetectContentType(buf[:n])

	_, err = db.Exec("INSERT INTO images (id, content_type, path) VALUES (?, ?, ?)", id, contentType, filePath)
	if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"id": id})
}

func handleGetImage(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract imageId from path /images/{imageId}
	imageId := r.URL.Path[len("/images/"):]
	if imageId == "" {
		sendError(w, "Image ID is required", http.StatusBadRequest)
		return
	}

	var meta ImageMetadata
	err := db.QueryRow("SELECT id, content_type, path FROM images WHERE id = ?", imageId).Scan(&meta.ID, &meta.ContentType, &meta.FilePath)
	if err == sql.ErrNoRows {
		sendError(w, "Image not found", http.StatusNotFound)
		return
	} else if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Set Content-Type to preserve original image type
	w.Header().Set("Content-Type", meta.ContentType)
	// Content-Disposition: inline ensures it's viewed in browser, not downloaded
	w.Header().Set("Content-Disposition", "inline")

	http.ServeFile(w, r, meta.FilePath)
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": message})
}