package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/google/uuid"
)

func main() {
	http.HandleFunc("/create-gif", createGifHandler)

	log.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}

func createGifHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form
	err := r.ParseMultipartForm(32 << 20) // 32MB
	if err != nil {
		sendJSONError(w, "Failed to parse multipart form", http.StatusBadRequest)
		return
	}

	// Get targetSize
	targetSize := r.FormValue("targetSize")
	if targetSize == "" {
		sendJSONError(w, "targetSize is required", http.StatusBadRequest)
		return
	}

	// Get delay
	delayStr := r.FormValue("delay")
	delay := 10 // default
	if delayStr != "" {
		d, err := strconv.Atoi(delayStr)
		if err == nil {
			delay = d
		}
	}

	// Get appendReverted
	appendReverted := r.FormValue("appendReverted") == "true"

	// Get images
	files := r.MultipartForm.File["images"]
	if len(files) == 0 {
		sendJSONError(w, "images are required", http.StatusBadRequest)
		return
	}

	// Create temporary directory for processing
	tempDir, err := os.MkdirTemp("", "gif-creator-")
	if err != nil {
		sendJSONError(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tempDir)

	var inputPaths []string
	for i, fileHeader := range files {
		f, err := fileHeader.Open()
		if err != nil {
			sendJSONError(w, "Failed to open image file", http.StatusBadRequest)
			return
		}
		defer f.Close()

		ext := filepath.Ext(fileHeader.Filename)
		if ext == "" {
			ext = ".tmp"
		}
		path := filepath.Join(tempDir, fmt.Sprintf("img_%d%s", i, ext))
		
		dst, err := os.Create(path)
		if err != nil {
			sendJSONError(w, "Failed to save image", http.StatusInternalServerError)
			return
		}
		defer dst.Close()

		if _, err := io.Copy(dst, f); err != nil {
			sendJSONError(w, "Failed to save image", http.StatusInternalServerError)
			return
		}
		inputPaths = append(inputPaths, path)
	}

	// Handle appendReverted logic
	var finalInputs []string
	finalInputs = append(finalInputs, inputPaths...)
	if appendReverted {
		for i := len(inputPaths) - 1; i >= 0; i-- {
			finalInputs = append(finalInputs, inputPaths[i])
		}
	}

	// Prepare ImageMagick command
	// -delay is in ticks (usually 1/100th of a second), so ms / 10
	delayTicks := delay / 10
	outputGIF := filepath.Join(tempDir, uuid.New().String()+".gif")

	args := []string{
		"convert",
		"-delay", strconv.Itoa(delayTicks),
		"-resize", targetSize,
		"-loop", "0",
	}
	args = append(args, finalInputs...)
	args = append(args, outputGIF)

	cmd := exec.Command(args...)
	if err := cmd.Run(); err != nil {
		log.Printf("ImageMagick error: %v", err)
		sendJSONError(w, "Failed to create GIF", http.StatusInternalServerError)
		return
	}

	// Serve the resulting GIF
	gifFile, err := os.Open(outputGIF)
	if err != nil {
		sendJSONError(w, "Failed to read generated GIF", http.StatusInternalServerError)
		return
	}
	defer gifFile.Close()

	w.Header().Set("Content-Type", "image/gif")
	io.Copy(w, gifFile)
}

func sendJSONError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	fmt.Fprintf(w, `{"error": "%s"}`, strings.ReplaceAll(message, `"`, `\"`))
}