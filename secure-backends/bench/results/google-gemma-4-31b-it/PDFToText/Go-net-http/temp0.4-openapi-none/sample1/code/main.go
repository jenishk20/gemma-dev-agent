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

	file, _, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Bad Request: Missing file in request", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Create a temporary file to store the uploaded PDF
	tempPdf, err := os.CreateTemp("", "upload-*.pdf")
	if err != nil {
		http.Error(w, "Internal Server Error: Failed to create temp file", http.StatusInternalServerError)
		return
	}
	defer os.Remove(tempPdf.Name())

	if _, err := io.Copy(tempPdf, file); err != nil {
		http.Error(w, "Internal Server Error: Failed to save upload", http.StatusInternalServerError)
		return
	}
	tempPdf.Close()

	// Create a temporary file for the output text
	tempTxt, err := os.CreateTemp("", "output-*.txt")
	if err != nil {
		http.Error(w, "Internal Server Error: Failed to create output file", http.StatusInternalServerError)
		return
	}
	tempTxtPath := tempTxt.Name()
	tempTxt.Close()
	defer os.Remove(tempTxtPath)

	// Execute pdftotext utility
	// Usage: pdftotext [input-pdf] [output-txt]
	cmd := exec.Command("pdftotext", tempPdf.Name(), tempTxtPath)
	if err := cmd.Run(); err != nil {
		http.Error(w, fmt.Sprintf("Internal Server Error: Conversion failed: %v", err), http.StatusInternalServerError)
		return
	}

	// Read the resulting text file
	content, err := os.ReadFile(tempTxtPath)
	if err != nil {
		http.Error(w, "Internal Server Error: Failed to read converted text", http.StatusInternalServerError)
		return
	}

	// Return as plain text
	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write(content)
}

func main() {
	http.HandleFunc("/convert", convertHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed to start: %v\n", err)
		os.Exit(1)
	}
}