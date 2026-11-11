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

func main() {
	http.HandleFunc("/concatenate", concatenateHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed: %s\n", err)
		os.Exit(1)
	}
}

func concatenateHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form
	err := r.ParseMultipartForm(32 << 20) // 32MB max memory
	if err != nil {
		sendError(w, "Invalid input or missing files.", http.StatusBadRequest)
		return
	}

	files, err := r.MultipartForm.File["files"]
	if err != nil || len(files) == 0 {
		sendError(w, "Invalid input or missing files.", http.StatusBadRequest)
		return
	}

	// Create a temporary directory for this request to avoid collisions
	tempDir, err := os.MkdirTemp("", "pdf-concat-")
	if err != nil {
		sendError(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tempDir)

	var inputPaths []string
	for i, fileHeader := range files {
		f, err := fileHeader.Open()
		if err != nil {
			sendError(w, "Error reading uploaded file", http.StatusBadRequest)
			return
		}

		filePath := filepath.Join(tempDir, fmt.Sprintf("input_%d.pdf", i))
		out, err := os.Create(filePath)
		if err != nil {
			f.Close()
			sendError(w, "Internal Server Error", http.StatusInternalServerError)
			return
		}

		_, err = io.Copy(out, f)
		f.Close()
		out.Close()

		if err != nil {
			sendError(w, "Error saving uploaded file", http.StatusInternalServerError)
			return
		}
		inputPaths = append(inputPaths, filePath)
	}

	// Output file path
	outputFileName := fmt.Sprintf("output_%s.pdf", uuid.NewString())
	outputPath := filepath.Join(tempDir, outputFileName)

	// Prepare pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
	args := append(inputPaths, outputPath)
	cmd := exec.Command("pdfunite", args...)
	if err := cmd.Run(); err != nil {
		sendError(w, "An error occurred while processing the files.", http.StatusInternalServerError)
		return
	}

	// Serve the resulting PDF
	resultFile, err := os.Open(outputPath)
	if err != nil {
		sendError(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	defer resultFile.Close()

	w.Header().Set("Content-Type", "application/pdf")
	w.Header().Set("Content-Disposition", "attachment; filename=concatenated.pdf")
	io.Copy(w, resultFile)
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{Error: message})
}