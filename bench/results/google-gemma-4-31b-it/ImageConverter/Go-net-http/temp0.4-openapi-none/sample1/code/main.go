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
	err := r.ParseMultipartForm(32 << 20) // 32MB max memory
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

	var imagePaths []string
	for i, fileHeader := range files {
		file, err := fileHeader.Open()
		if err != nil {
			sendError(w, fmt.Sprintf("Failed to open image %d", i), http.StatusBadRequest)
			return
		}
		defer file.Close()

		path := filepath.Join(tempDir, fmt.Sprintf("img_%d", i))
		out, err := os.Create(path)
		if err != nil {
			sendError(w, "Internal server error saving image", http.StatusInternalServerError)
			return
		}
		io.Copy(out, file)
		out.Close()
		imagePaths = append(imagePaths, path)
	}

	// Handle appendReverted: duplicate images in reverse order
	if appendReverted {
		for i := len(imagePaths) - 1; i >= 0; i-- {
			path := filepath.Join(tempDir, fmt.Sprintf("rev_%d", i))
			input, _ := os.ReadFile(imagePaths[i])
			os.WriteFile(path, input, 0644)
			imagePaths = append(imagePaths, path)
		}
	}

	// Prepare output path
	outputFileName := uuid.New().String() + ".gif"
	outputPath := filepath.Join(tempDir, outputFileName)

	// Build ImageMagick command
	// -delay is in ticks (1/100th of a second), so we divide ms by 10
	delayTicks := delay / 10
	args := []string{
		"convert",
		"-delay", strconv.Itoa(delayTicks),
		"-resize", targetSize,
		"-loop", "0",
	}
	args = append(args, imagePaths...)
	args = append(args, outputPath)

	cmd := exec.Command("convert", args[1:]...) // args[0] is "convert"
	if err := cmd.Run(); err != nil {
		log.Printf("ImageMagick error: %v", err)
		sendError(w, "Failed to create GIF using ImageMagick", http.StatusInternalServerError)
		return
	}

	// Serve the resulting GIF
	gifData, err := os.ReadFile(outputPath)
	if err != nil {
		sendError(w, "Failed to read generated GIF", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "image/gif")
	w.WriteHeader(http.StatusOK)
	w.Write(gifData)
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{Error: message})
}