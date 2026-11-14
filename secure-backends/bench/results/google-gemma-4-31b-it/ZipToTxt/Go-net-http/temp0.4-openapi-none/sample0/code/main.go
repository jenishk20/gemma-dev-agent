package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"net/http"
	"path/filepath"
	"strings"
)

// handleConvert processes the multipart/form-data request and converts the zip file to text
func handleConvert(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Limit upload size to 10MB to prevent DoS
	r.Body = http.MaxBytesReader(w, r.Body, 10<<20)

	// Parse the multipart form
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Invalid input: could not parse form", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Invalid input: missing 'file' field", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Read the uploaded file into a buffer for zip.NewReader
	var buf bytes.Buffer
	if _, err := io.Copy(&buf, file); err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Zip reader requires the size of the archive
	reader, err := zip.NewReader(&buf, int64(buf.Len()))
	if err != nil {
		http.Error(w, "Invalid zip file", http.StatusBadRequest)
		return
	}

	var result strings.Builder
	for _, f := range reader.File {
		// Only process files (not directories) and only those with .txt extension
		if f.FileInfo().IsDir() || filepath.Ext(f.Name) != ".txt" {
			continue
		}

		rc, err := f.Open()
		if err != nil {
			continue // Skip files that cannot be opened
		}

		content, err := io.ReadAll(rc)
		rc.Close()
		if err != nil {
			continue // Skip files that cannot be read
		}

		result.Write(content)
		result.WriteString("\n") // Ensure separation between files
	}

	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, result.String())
}

func main() {
	http.HandleFunc("/convert", handleConvert)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed to start: %v\n", err)
	}
}