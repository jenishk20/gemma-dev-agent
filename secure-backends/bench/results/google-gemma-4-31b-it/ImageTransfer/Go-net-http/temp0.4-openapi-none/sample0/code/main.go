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
	"strings"

	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

const (
	uploadDir = "./uploads"
	dbPath    = "./images.db"
	port      = ":5000"
)

type ImageMetadata struct {
	ID       string `json:"id"`
	MimeType string `json:"mime_type"`
	Path     string `json:"path"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `CREATE TABLE IF NOT EXISTS images (id TEXT PRIMARY KEY, mime_type TEXT, path TEXT);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func uploadHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form
	err := r.ParseMultipartForm(10 << 20) // 10MB limit
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
	filename := id + ext
	fullPath := filepath.Join(uploadDir, filename)

	// Save file to disk
	out, err := os.Create(fullPath)
	if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer out.Close()

	_, err = io.Copy(out, file)
	if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Detect MimeType
	mimeType := http.DetectContentType(nil) // Placeholder, we'll read the start of the file
	// Re-read first 512 bytes for actual detection
	out.Seek(0, 0)
	buffer := make([]byte, 512)
	n, _ := out.Read(buffer)
	mimeType = http.DetectContentType(buffer[:n])

	// Store in DB
	_, err = db.Exec("INSERT INTO images (id, mime_type, path) VALUES (?, ?, ?)", id, mimeType, fullPath)
	if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"id": id})
}

func serveImageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract imageId from path /images/{imageId}
	pathParts := strings.Split(r.URL.Path, "/")
	if len(pathParts) < 3 {
		sendError(w, "Image ID is required", http.StatusBadRequest)
		return
	}
	imageId := pathParts[2]

	var mimeType, filePath string
	err := db.QueryRow("SELECT mime_type, path FROM images WHERE id = ?", imageId).Scan(&mimeType, &filePath)
	if err == sql.ErrNoRows {
		sendError(w, "Image not found", http.StatusNotFound)
		return
	} else if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// To ensure the browser views the image instead of downloading it:
	// 1. Set the correct Content-Type
	// 2. Set Content-Disposition to inline
	w.Header().Set("Content-Type", mimeType)
	w.Header().Set("Content-Disposition", "inline")

	http.ServeFile(w, r, filePath)
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": message})
}

func main() {
	// Ensure upload directory exists
	if _, err := os.Stat(uploadDir); os.IsNotExist(err) {
		os.MkdirAll(uploadDir, 0755)
	}

	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/upload", uploadHandler)
	mux.HandleFunc("/images/", serveImageHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}