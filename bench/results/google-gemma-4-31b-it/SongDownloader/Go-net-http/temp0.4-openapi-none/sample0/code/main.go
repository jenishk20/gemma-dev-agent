package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

const songsDir = "/var/songs"

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

	// Prevent directory traversal attacks by cleaning the path 
	// and ensuring the resulting path is still within the songsDir
	safeFilename := filepath.Base(req.Filename)
	fullPath := filepath.Join(songsDir, safeFilename)

	file, err := os.Open(fullPath)
	if err != nil {
		if os.IsNotExist(err) {
			http.Error(w, "File does not exist", http.StatusNotFound)
		} else {
			http.Error(w, "Internal server error", http.StatusInternalServerError)
		}
		return
	}
	defer file.Close()

	// Set the content type to audio/mpeg as per OpenAPI spec
	w.Header().Set("Content-Type", "audio/mpeg")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", safeFilename))

	// Stream the file content to the response writer
	_, err = io.Copy(w, file)
	if err != nil {
		// Header is already sent, so we can't send a 500 here
		fmt.Printf("Error streaming file: %v\n", err)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/download", downloadHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	err := http.ListenAndServe("0.0.0.0:5000", mux)
	if err != nil {
		fmt.Printf("Server failed to start: %v\n", err)
		os.Exit(1)
	}
}