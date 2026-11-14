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
	err := r.ParseMultipartForm(100 << 20) // 100MB limit
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
	tmpDir, err := os.MkdirTemp("", "frameextract-*")
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tmpDir)

	// Save uploaded video to disk
	videoPath := filepath.Join(tmpDir, "input_video")
	dst, err := os.Create(videoPath)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	if _, err := io.Copy(dst, file); err != nil {
		dst.Close()
		http.Error(w, "Error saving video", http.StatusInternalServerError)
		return
	}
	dst.Close()

	// Output path for the frame
	outputImage := filepath.Join(tmpDir, "frame.png")

	// ffmpeg command: extract a single frame at the specified index
	// -i: input file
	// -vf "select=eq(n\,FRAME_INDEX)": filter to select specific frame index
	// -vframes 1: output exactly one frame
	cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n\\,%d)", frameNumber), "-vframes", "1", "-f", "image2", outputImage)
	
	if err := cmd.Run(); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprintf(w, `{"error": "Frame at index %d could not be found."}`, frameNumber)
		return
	}

	// Read the extracted image and send it back
	imgData, err := os.ReadFile(outputImage)
	if err != nil {
		http.Error(w, "Error reading extracted frame", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "image/png")
	w.Write(imgData)
}