package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
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

	// Prevent directory traversal attacks by cleaning the path and checking the base
	safeFilename := filepath.Base(req.Filename)
	fullPath := filepath.Join(songsDir, safeFilename)

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

	// Set the content type as specified in the OpenAPI schema
	w.Header().Set("Content-Type", "audio/mpeg")
	w.Header().Set("Content-Length", fmt.Sprintf("%d", info.Size()))

	// Stream the file content to the response writer
	_, err = io.Copy(w, file)
	if err != nil {
		// Header already sent, cannot send 500 here
		return
	}
}

func main() {
	http.HandleFunc("/download", downloadHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Error starting server: %s\n", err)
		os.Exit(1)
	}
}