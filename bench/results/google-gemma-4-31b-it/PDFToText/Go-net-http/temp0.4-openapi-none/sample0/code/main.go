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

	// Limit upload size to 10MB
	r.Body = http.MaxBytesReader(w, r.Body, 10<<20)

	// Parse multipart form
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Bad Request - Invalid input", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Bad Request - Missing file", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Validate file extension
	if filepath.Ext(header.Filename) != ".pdf" {
		http.Error(w, "Bad Request - File must be a PDF", http.StatusBadRequest)
		return
	}

	// Create a temporary file to store the uploaded PDF
	tempPdf, err := os.CreateTemp("", "upload-*.pdf")
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	defer os.Remove(tempPdf.Name())

	if _, err := io.Copy(tempPdf, file); err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	tempPdf.Close()

	// Create a temporary file for the output text
	tempTxt, err := os.CreateTemp("", "output-*.txt")
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	tempTxtPath := tempTxt.Name()
	tempTxt.Close()
	defer os.Remove(tempTxtPath)

	// Execute pdftotext utility
	// pdftotext [input-pdf] [output-text]
	cmd := exec.Command("pdftotext", tempPdf.Name(), tempTxtPath)
	if err := cmd.Run(); err != nil {
		http.Error(w, "Internal Server Error - Conversion failed", http.StatusInternalServerError)
		return
	}

	// Read the resulting text file
	content, err := os.ReadFile(tempTxtPath)
	if err != nil {
		http.Error(w, "Internal Server Error - Failed to read output", http.StatusInternalServerError)
		return
	}

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