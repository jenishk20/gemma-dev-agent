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
	http.HandleFunc("/extract", extractHandler)
	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		panic(err)
	}
}

func extractHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form
	err := r.ParseMultipartForm(32 << 20) // 32MB
	if err != nil {
		http.Error(w, "Error parsing form", http.StatusBadRequest)
		return
	}

	frameNumberStr := r.FormValue("frameNumber")
	frameNumber, err := strconv.Atoi(frameNumberStr)
	if err != nil {
		http.Error(w, "Invalid frameNumber", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("video")
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

	videoPath := filepath.Join(tempDir, header.Filename)
	outPath := filepath.Join(tempDir, "frame.png")

	// Save uploaded video to disk
	dst, err := os.Create(videoPath)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer dst.Close()
	if _, err := io.Copy(dst, file); err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// FFmpeg command to extract a specific frame
	// -i: input file
	// -vf "select=eq(n\,FRAME_INDEX)": select the frame with index X
	// -vframes 1: output exactly one frame
	cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n\\,%d)", frameNumber), "-vframes", "1", outPath)
	
	if err := cmd.Run(); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprintf(w, `{"error": "Frame at index %d could not be found."}`, frameNumber)
		return
	}

	// Read the resulting image
	imgData, err := os.ReadFile(outPath)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "image/png")
	w.WriteHeader(http.StatusOK)
	w.Write(imgData)
}