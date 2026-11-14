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

type ErrorResponse struct {
	Error string `json:"error"`
}

func concatenateHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form (max 32MB in memory)
	err := r.ParseMultipartForm(32 << 20)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintf(w, `{"error": "Invalid input or missing files."}`)
		return
	}

	files := r.MultipartForm.File["files"]
	if len(files) == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintf(w, `{"error": "Invalid input or missing files."}`)
		return
	}

	// Create a temporary directory for this request
	tempDir, err := os.MkdirTemp("", "pdf-concat-")
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprintf(w, `{"error": "An error occurred while processing the files."}`)
		return
	}
	defer os.RemoveAll(tempDir)

	var inputPaths []string
	for i, fileHeader := range files {
		f, err := fileHeader.Open()
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			fmt.Fprintf(w, `{"error": "Could not open uploaded file."}`)
			return
		}

		path := filepath.Join(tempDir, fmt.Sprintf("input_%d.pdf", i))
		dst, err := os.Create(path)
		if err != nil {
			f.Close()
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			fmt.Fprintf(w, `{"error": "Could not save uploaded file."}`)
			return
		}

		_, err = io.Copy(dst, f)
		f.Close()
		dst.Close()
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			fmt.Fprintf(w, `{"error": "Failed to write file to disk."}`)
			return
		}
		inputPaths = append(inputPaths, path)
	}

	// Define output path
	outputFileName := uuid.New().String() + ".pdf"
	outputPath := filepath.Join(tempDir, outputFileName)

	// Build pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
	args := append(inputPaths, outputPath)
	cmd := exec.Command("pdfunite", args...)
	if err := cmd.Run(); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprintf(w, `{"error": "An error occurred while processing the files."}`)
		return
	}

	// Serve the resulting PDF
	resultFile, err := os.Open(outputPath)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprintf(w, `{"error": "Could not read concatenated file."}`)
		return
	}
	defer resultFile.Close()

	w.Header().Set("Content-Type", "application/pdf")
	w.WriteHeader(http.StatusOK)
	io.Copy(w, resultFile)
}

func main() {
	http.HandleFunc("/concatenate", concatenateHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed: %s\n", err)
		os.Exit(1)
	}
}