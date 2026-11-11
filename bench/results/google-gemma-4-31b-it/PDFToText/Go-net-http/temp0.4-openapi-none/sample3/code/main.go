package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

func convertHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form (max 10MB)
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Bad Request: Could not parse form", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Bad Request: Missing file in request", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Create a temporary file to store the uploaded PDF
	tempPdfPath, err := os.CreateTemp("", "upload-*.pdf")
	if err != nil {
		http.Error(w, "Internal Server Error: Failed to create temp file", http.StatusInternalServerError)
		return
	}
	defer os.Remove(tempPdfPath.Name())

	_, err = io.Copy(tempPdfPath, file)
	if err != nil {
		http.Error(w, "Internal Server Error: Failed to save upload", http.StatusInternalServerError)
		return
	}
	tempPdfPath.Close()

	// Create a temporary file for the output text
	tempTxtPath := filepath.Join(os.TempDir(), fmt.Sprintf("%s.txt", filepath.Base(tempPdfPath.Name())))
	defer os.Remove(tempTxtPath)

	// Execute pdftotext utility
	// pdftotext [input-pdf] [output-text-file]
	cmd := exec.Command("pdftotext", tempPdfPath.Name(), tempTxtPath)
	if err := cmd.Run(); err != nil {
		http.Error(w, "Internal Server Error: PDF conversion failed", http.StatusInternalServerError)
		return
	}

	// Read the extracted text
	text, err := os.ReadFile(tempTxtPath)
	if err != nil {
		http.Error(w, "Internal Server Error: Failed to read converted text", http.StatusInternalServerError)
		return
	}

	// Return as plain text
	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write(text)
}

func main() {
	http.HandleFunc("/convert", convertHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed: %s\n", err)
		os.Exit(1)
	}
}