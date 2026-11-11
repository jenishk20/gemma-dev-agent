package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/google/uuid"
)

func convertHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	// Limit upload size to 10MB
	r.Body = http.MaxBytesReader(w.Request.Body, 10*1024*1024)

	// Parse multipart form
	err := r.ParseMultipartForm(10 * 1024 * 1024)
	if err != nil {
		http.Error(w, "Bad Request: Could not parse form", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Bad Request: Missing file field", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Basic validation for PDF extension
	if filepath.Ext(header.Filename) != ".pdf" {
		http.Error(w, "Bad Request: File must be a PDF", http.StatusBadRequest)
		return
	}

	// Create temporary files for input and output
	tempID := uuid.New().String()
	inputPath := filepath.Join(os.TempDir(), tempID+".pdf")
	outputPath := filepath.Join(os.TempDir(), tempID+".txt")

	// Save uploaded file to disk
	dst, err := os.Create(inputPath)
	if err != nil {
		http.Error(w, "Internal Server Error: Could not create temp file", http.StatusInternalServerError)
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		http.Error(w, "Internal Server Error: Failed to save file", http.StatusInternalServerError)
		return
	}

	// Cleanup temp files after request
	defer os.Remove(inputPath)
	defer os.Remove(outputPath)

	// Execute pdftotext utility
	// -layout preserves the layout of the text
	cmd := exec.Command("pdftotext", "-layout", inputPath, outputPath)
	if err := cmd.Run(); err != nil {
		http.Error(w, fmt.Sprintf("Internal Server Error: Conversion failed: %v", err), http.StatusInternalServerError)
		return
	}

	// Read the resulting text file
	content, err := os.ReadFile(outputPath)
	if err != nil {
		http.Error(w, "Internal Server Error: Failed to read output", http.StatusInternalServerError)
		return
	}

	// Return plain text response
	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write(content)
}

func main() {
	http.HandleFunc("/convert", convertHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Error starting server: %s\n", err)
		os.Exit(1)
	}
}