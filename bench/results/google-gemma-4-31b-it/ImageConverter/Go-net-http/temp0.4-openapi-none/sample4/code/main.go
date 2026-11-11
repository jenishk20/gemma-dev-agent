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
	http.HandleFunc("/create-gif", handleCreateGif)

	log.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}

func handleCreateGif(w http.ResponseWriter, r *http.Request) {
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

	// Target Size
	targetSize := r.FormValue("targetSize")
	if targetSize == "" {
		sendError(w, "targetSize is required", http.StatusBadRequest)
		return
	}

	// Delay
	delayStr := r.FormValue("delay")
	delay := 10 // default
	if delayStr != "" {
		if d, err := strconv.Atoi(delayStr); err == nil {
			delay = d
		}
	}

	// Append Reverted
	appendReverted := r.FormValue("appendReverted") == "true"

	// Images
	files := r.MultipartForm.File["images"]
	if len(files) == 0 {
		sendError(w, "images are required", http.StatusBadRequest)
		return
	}

	// Create temporary directory for processing
	tempDir, err := os.MkdirTemp("", "gif-creator-")
	if err != nil {
		sendError(w, "Internal server error creating temp dir", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tempDir)

	var inputPaths []string
	for i, fileHeader := range files {
		file, err := fileHeader.Open()
		if err != nil {
			sendError(w, fmt.Sprintf("Error opening image %d", i), http.StatusBadRequest)
			return
		}
		defer file.Close()

		path := filepath.Join(tempDir, fmt.Sprintf("img_%d%s", i, filepath.Ext(fileHeader.Filename)))
		out, err := os.Create(path)
		if err != nil {
			sendError(w, "Internal server error saving image", http.StatusInternalServerError)
			return
		}
		io.Copy(out, file)
		out.Close()
		inputPaths = append(inputPaths, path)
	}

	// Handle reversed sequence
	var finalPaths []string
	finalPaths = append(finalPaths, inputPaths...)
	if appendReverted {
		for i := len(inputPaths) - 2; i >= 0; i-- {
			finalPaths = append(finalPaths, inputPaths[i])
		}
	}

	outputGif := filepath.Join(tempDir, uuid.New().String()+".gif")

	// ImageMagick convert command
	// -delay is in ticks (1/100th of a second), so we divide ms by 10
	delayTicks := strconv.Itoa(delay / 10)
	
	args := []string{
		"-delay", delayTicks,
		"-resize", targetSize,
		"-loop", "0",
	}
	args = append(args, finalPaths...)
	args = append(args, outputGif)

	cmd := exec.Command("convert", args...)
	if err := cmd.Run(); err != nil {
		sendError(w, "ImageMagick conversion failed: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Serve the resulting GIF
	gifData, err := os.ReadFile(outputGif)
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