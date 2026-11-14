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

	targetSize := r.FormValue("targetSize")
	if targetSize == "" {
		sendError(w, "targetSize is required", http.StatusBadRequest)
		return
	}

	delayStr := r.FormValue("delay")
	delay := 10 // default
	if delayStr != "" {
		if d, err := strconv.Atoi(delayStr); err == nil {
			delay = d
		}
	}

	appendReverted := r.FormValue("appendReverted") == "true"

	files := r.MultipartForm.File["images"]
	if len(files) == 0 {
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
			sendError(w, fmt.Sprintf("Error opening file %d", i), http.StatusBadRequest)
			return
		}
		
		filePath := filepath.Join(tempDir, fmt.Sprintf("img_%d%s", i, filepath.Ext(fileHeader.Filename)))
		out, err := os.Create(filePath)
		if err != nil {
			f.Close()
			sendError(w, "Internal server error saving file", http.StatusInternalServerError)
			return
		}
		
		_, err = io.Copy(out, f)
		out.Close()
		f.Close()
		if err != nil {
			sendError(w, "Internal server error copying file", http.StatusInternalServerError)
			return
		}
		inputPaths = append(inputPaths, filePath)
	}

	// Handle appendReverted logic
	var finalPaths []string
	finalPaths = append(finalPaths, inputPaths...)
	if appendReverted {
		for i := len(inputPaths) - 2; i >= 0; i-- {
			finalPaths = append(finalPaths, inputPaths[i])
		}
	}

	outputGifPath := filepath.Join(tempDir, uuid.New().String()+".gif")

	// ImageMagick convert command:
	// -delay: delay between frames (1/100th of a second in IM, but schema says ms, so we approximate or use -delay)
	// -loop 0: infinite loop
	// -resize: target size
	// -layers composite or just sequence
	
	// ImageMagick's -delay is in ticks (usually 1/100s). 
	// To get ms, we divide by 10.
	imDelay := strconv.Itoa(delay / 10)
	if imDelay == "0" && delay > 0 {
		imDelay = "1"
	}

	args := []string{
		"-delay", imDelay,
		"-loop", "0",
		"-resize", targetSize,
	}
	args = append(args, finalPaths...)
	args = append(args, outputGifPath)

	cmd := exec.Command("convert", args...)
	if err := cmd.Run(); err != nil {
		sendError(w, "ImageMagick conversion failed: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Serve the resulting GIF
	gifData, err := os.ReadFile(outputGifPath)
	if err != nil {
		sendError(w, "Internal server error reading result", http.StatusInternalServerError)
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