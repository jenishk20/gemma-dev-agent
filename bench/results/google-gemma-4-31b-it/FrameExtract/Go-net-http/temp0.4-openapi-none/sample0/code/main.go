package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
)

func main() {
	http.HandleFunc("/extract", extractFrameHandler)
	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Error starting server: %s\n", err)
	}
}

func extractFrameHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form
	err := r.ParseMultipartForm(32 << 20) // 32MB max memory
	if err != nil {
		http.Error(w, "Error parsing form", http.StatusBadRequest)
		return
	}

	// Get frame number
	frameStr := r.FormValue("frameNumber")
	frameNumber, err := strconv.Atoi(frameStr)
	if err != nil {
		http.Error(w, "Invalid frameNumber", http.StatusBadRequest)
		return
	}

	// Get video file
	file, _, err := r.FormFile("video")
	if err != nil {
		http.Error(w, "Video file is missing", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Create temporary directory for processing
	tempDir, err := os.MkdirTemp("", "frameextract")
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tempDir)

	// Save uploaded video to temp file
	videoPath := filepath.Join(tempDir, "input_video")
	dst, err := os.Create(videoPath)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	if _, err := io.Copy(dst, file); err != nil {
		dst.Close()
		http.Error(w, "Error saving upload", http.StatusInternalServerError)
		return
	}
	dst.Close()

	// Output path for the extracted frame
	outputPath := filepath.Join(tempDir, "frame.png")

	// ffmpeg command: extract a single frame at the specified index
	// -i: input file
	// -vf "select=eq(n,X)": select frame X
	// -vframes 1: output exactly one frame
	cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n,%d)", frameNumber), "-vframes", "1", outputPath)
	
	if err := cmd.Run(); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprintf(w, `{"error": "Frame at index %d could not be found."}`, frameNumber)
		return
	}

	// Read the resulting image and serve it
	imgData, err := os.ReadFile(outputPath)
	if err != nil {
		http.Error(w, "Error reading extracted frame", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "image/png")
	w.Write(imgData)
}