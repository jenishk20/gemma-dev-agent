package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/google/uuid"
)

type ErrorResponse struct {
	Error string `json:"error"`
}

func handleConcatenate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form
	err := r.ParseMultipartForm(32 << 20) // 32MB max memory
	if err != nil {
		sendError(w, "Invalid input or missing files.", http.StatusBadRequest)
		return
	}

	files := r.MultipartForm.File["files"]
	if len(files) == 0 {
		sendError(w, "Invalid input or missing files.", http.StatusBadRequest)
		return
	}

	// Create a temporary directory for this request
	tempDir, err := os.MkdirTemp("", "pdf-concat-")
	if err != nil {
		sendError(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tempDir)

	var inputPaths []string
	for i, fileHeader := range files {
		file, err := fileHeader.Open()
		if err != nil {
			sendError(w, "Error opening uploaded file", http.StatusBadRequest)
			return
		}
		defer file.Close()

		path := filepath.Join(tempDir, fmt.Sprintf("input_%d.pdf", i))
		dst, err := os.Create(path)
		if err != nil {
			sendError(w, "Error saving uploaded file", http.StatusInternalServerError)
			return
		}
		defer dst.Close()

		if _, err := io.Copy(dst, file); err != nil {
			sendError(w, "Error saving uploaded file", http.StatusInternalServerError)
			return
		}
		inputPaths = append(inputPaths, path)
	}

	// Output path
	outputFileName := uuid.New().String() + ".pdf"
	outputPath := filepath.Join(tempDir, outputFileName)

	// Prepare pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
	args := append(inputPaths, outputPath)
	cmd := exec.Command("pdfunite", args...)
	if err := cmd.Run(); err != nil {
		sendError(w, "An error occurred while processing the files.", http.StatusInternalServerError)
		return
	}

	// Serve the resulting PDF
	content, err := os.ReadFile(outputPath)
	if err != nil {
		sendError(w, "Error reading resulting PDF", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/pdf")
	w.WriteHeader(http.StatusOK)
	w.Write(content)
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{Error: message})
}

func main() {
	http.HandleFunc("/concatenate", handleConcatenate)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed: %s\n", err)
		os.Exit(1)
	}
}