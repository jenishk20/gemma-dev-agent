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
	dbFile    = "images.db"
	port      = ":5000"
)

type ImageMetadata struct {
	ID       string
	MimeType string
	Path     string
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", dbFile)
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

	file, header, err := r.FormFile("file")
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "Invalid input: file field is required"})
		return
	}
	defer file.Close()

	id := uuid.New().String()
	mimeType := http.DetectContentType(make([]byte, 512))
	// Re-read the first 512 bytes for accurate detection
	buffer := make([]byte, 512)
	n, _ := file.Read(buffer)
	mimeType = http.DetectContentType(buffer[:n])
	file.Seek(0, io.SeekStart)

	filePath := filepath.Join(uploadDir, id+filepath.Ext(header.Filename))
	
	out, err := os.Create(filePath)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "Internal server error saving file"})
		return
	}
	defer out.Close()

	_, err = io.Copy(out, file)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "Internal server error during upload"})
		return
	}

	_, err = db.Exec("INSERT INTO images (id, mime_type, path) VALUES (?, ?, ?)", id, mimeType, filePath)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "Internal server error saving metadata"})
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

	imageId := r.URL.Path[len("/images/"):]
	if imageId == "" {
		http.Error(w, "Image ID is required", http.StatusBadRequest)
		return
	}

	var meta ImageMetadata
	err := db.QueryRow("SELECT id, mime_type, path FROM images WHERE id = ?", imageId).Scan(&meta.ID, &meta.MimeType, &meta.Path)
	if err == sql.ErrNoRows {
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "Image not found"})
		return
	} else if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "Internal server error"})
		return
	}

	// To ensure it's viewable in browser and not downloaded:
	// 1. Set correct Content-Type
	// 2. Set Content-Disposition to inline
	w.Header().Set("Content-Type", meta.MimeType)
	w.Header().Set("Content-Disposition", "inline")

	http.ServeFile(w, r, meta.Path)
}

func main() {
	if _, err := os.Stat(uploadDir); os.IsNotExist(err) {
		os.MkdirAll(uploadDir, 0755)
	}

	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/upload", uploadHandler)
	mux.HandleFunc("/images/", serveImageHandler)

	fmt.Printf("Server starting on 0.0.0.0:5000...\n")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}