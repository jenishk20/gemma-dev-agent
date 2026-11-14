package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

const songsDirectory = "/var/songs"

type DownloadRequest struct {
	Filename string `json:"filename"`
}

func downloadHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req DownloadRequest
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if req.Filename == "" {
		http.Error(w, "Filename is required", http.StatusBadRequest)
		return
	}

	// Security: Prevent directory traversal attacks by cleaning the path 
	// and ensuring the resulting path is still within the songsDirectory.
	safeFilename := filepath.Base(req.Filename)
	fullPath := filepath.Join(songsDirectory, safeFilename)

	// Verify the file exists and is not a directory
	info, err := os.Stat(fullPath)
	if os.IsNotExist(err) || info.IsDir() {
		http.Error(w, "File does not exist", http.StatusNotFound)
		return
	}

	file, err := os.Open(fullPath)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer file.Close()

	// Set the content type to audio/mpeg as per OpenAPI spec
	w.Header().Set("Content-Type", "audio/mpeg")
	w.Header().Set("Content-Length", fmt.Sprintf("%d", info.Size()))

	// Stream the file content to the response writer
	_, err = io.Copy(w, file)
	if err != nil {
		log.Printf("Error streaming file: %v", err)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/download", downloadHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	err := http.ListenAndServe("0.0.0.0:5000", mux)
	if err != nil {
		log.Fatal(err)
	}
}