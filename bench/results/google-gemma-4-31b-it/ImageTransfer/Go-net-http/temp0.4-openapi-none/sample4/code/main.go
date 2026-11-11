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
	dbPath    = "./images.db"
	port      = "0.0.0.0:5000"
)

type ImageMetadata struct {
	ID       string
	MimeType string
	Path     string
}

type ResponseError struct {
	Error string `json:"error"`
}

type ResponseID struct {
	ID string `json:"id"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}

	statement := `CREATE TABLE IF NOT EXISTS images (id TEXT PRIMARY KEY, mime_type TEXT, path TEXT);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}
}

func uploadHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Limit upload size to 10MB
	r.Body = http.MaxBytesReader(w, r.Body, 10<<20)

	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		sendError(w, "Invalid multipart form", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		sendError(w, "File field 'file' is missing", http.StatusBadRequest)
		return
	}
	defer file.Close()

	id := uuid.New().String()
	mimeType := http.DetectContentType(make([]byte, 512)) // Initial guess
	// Read first 512 bytes for better detection
	buffer := make([]byte, 512)
	n, _ := file.Read(buffer)
	mimeType = http.DetectContentType(buffer[:n])
	
	// Reset file pointer after reading for mime detection
	if _, err := file.Seek(0, io.SeekStart); err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	filePath := filepath.Join(uploadDir, id+filepath.Ext(header.Filename))
	dst, err := os.Create(filePath)
	if err != nil {
		sendError(w, "Failed to save file", http.StatusInternalServerError)
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		sendError(w, "Failed to write file", http.StatusInternalServerError)
		return
	}

	_, err = db.Exec("INSERT INTO images (id, mime_type, path) VALUES (?, ?, ?)", id, mimeType, filePath)
	if err != nil {
		sendError(w, "Failed to save metadata", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ResponseID{ID: id})
}

func serveImageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	imageId := r.URL.Path[len("/images/"):]
	if imageId == "" {
		sendError(w, "Image ID is required", http.StatusBadRequest)
		return
	}

	var meta ImageMetadata
	err := db.QueryRow("SELECT id, mime_type, path FROM images WHERE id = ?", imageId).Scan(&meta.ID, &meta.MimeType, &meta.Path)
	if err == sql.ErrNoRows {
		sendError(w, "Image not found", http.StatusNotFound)
		return
	} else if err != nil {
		sendError(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Set Content-Type to preserve original image type
	w.Header().Set("Content-Type", meta.MimeType)
	// Ensure it's viewed in browser (inline) and not downloaded
	w.Header().Set("Content-Disposition", "inline")

	http.ServeFile(w, r, meta.Path)
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ResponseError{Error: message})
}

func main() {
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		log.Fatal(err)
	}
	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/upload", uploadHandler)
	mux.HandleFunc("/images/", serveImageHandler)

	fmt.Printf("Server starting on %s\n", port)
	log.Fatal(http.ListenAndServe(port, mux))
}