package main

import (
	"encoding/json"
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

type ErrorResponse struct {
	Error string `json:"error"`
}

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
		sendError(w, "Failed to parse multipart form", http.StatusBadRequest)
		return
	}

	// Get targetSize
	targetSize := r.FormValue("targetSize")
	if targetSize == "" {
		sendError(w, "targetSize is required", http.StatusBadRequest)
		return
	}

	// Get delay
	delayStr := r.FormValue("delay")
	delay := 10 // default
	if delayStr != "" {
		d, err := strconv.Atoi(delayStr)
		if err != nil {
			sendError(w, "Invalid delay value", http.StatusBadRequest)
			return
		}
		delay = d
	}

	// Get appendReverted
	appendReverted := r.FormValue("appendReverted") == "true"

	// Get images
	files, err := r.MultipartForm.File["images"]
	if err != nil || len(files) == 0 {
		sendError(w, "images are required", http.StatusBadRequest)
		return
	}

	// Create a temporary directory for processing
	tempDir, err := os.MkdirTemp("", "gif-creator-")
	if err != nil {
		sendError(w, "Internal server error creating temp dir", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tempDir)

	var inputPaths []string
	for i, fileHeader := range files {
		f, err := fileHeader.Open()
		if err != nil {
			sendError(w, "Failed to open uploaded image", http.StatusBadRequest)
			return
		}
		defer f.Close()

		path := filepath.Join(tempDir, fmt.Sprintf("img_%d%s", i, filepath.Ext(fileHeader.Filename)))
		dst, err := os.Create(path)
		if err != nil {
			sendError(w, "Failed to save uploaded image", http.StatusInternalServerError)
			return
		}
		io.Copy(dst, f)
		dst.Close()
		inputPaths = append(inputPaths, path)
	}

	// Handle appendReverted: duplicate paths in reverse order
	if appendReverted {
		for i := len(inputPaths) - 1; i >= 0; i-- {
			inputPaths = append(inputPaths, inputPaths[i])
		}
	}

	// Output GIF path
	outputGif := filepath.Join(tempDir, uuid.New().String()+".gif")

	// ImageMagick convert command:
	// -delay: delay between frames (1/100th of a second, so we divide ms by 10)
	// -loop 0: infinite loop
	// -resize: target size
	// -set delay: ensures the delay is applied to each frame
	imgMagickDelay := delay / 10
	args := []string{
		"-delay", strconv.Itoa(imgMagickDelay),
		"-loop", "0",
		"-resize", targetSize,
	}
	args = append(args, inputPaths...)
	args = append(args, outputGif)

	cmd := exec.Command("convert", args...)
	if err := cmd.Run(); err != nil {
		sendError(w, fmt.Sprintf("ImageMagick conversion failed: %v", err), http.StatusInternalServerError)
		return
	}

	// Serve the resulting GIF
	gifFile, err := os.Open(outputGif)
	if err != nil {
		sendError(w, "Failed to read generated GIF", http.StatusInternalServerError)
		return
	}
	defer gifFile.Close()

	w.Header().Set("Content-Type", "image/gif")
	io.Copy(w, gifFile)
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{Error: message})
}