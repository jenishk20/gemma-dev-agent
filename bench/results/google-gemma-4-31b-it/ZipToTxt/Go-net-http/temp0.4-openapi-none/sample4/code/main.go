package main

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"log"
	"net/http"
	"path/filepath"
	"strings"
)

func convertHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Limit upload size to 10MB to prevent DOS
	r.Body = http.MaxBytesReader(w, r.Body, 10<<20)

	// Parse multipart form
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Invalid input: could not parse form", http.StatusBadRequest)
		return
	}

	file, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Invalid input: file field is required", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Read the zip file into memory
	buf := new(bytes.Buffer)
	if _, err := io.Copy(buf, file); err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// Open the zip archive
	zipReader, err := zip.NewReader(buf, int64(buf.Len()))
	if err != nil {
		http.Error(w, "Invalid zip file", http.StatusBadRequest)
		return
	}

	var result strings.Builder

	for _, f := range zipReader.Files {
		// Skip directories
		if f.FileInfo().IsDir() {
			continue
		}

		// Only process files with .txt extension (or similar text-based logic)
		// The prompt asks for "contents of all text files"
		if filepath.Ext(f.Name) == ".txt" {
			rc, err := f.Open()
			if err != nil {
				log.Printf("Error opening file %s: %v", f.Name, err)
				continue
			}

			content, err := io.ReadAll(rc)
			rc.Close()
			if err != nil {
				log.Printf("Error reading file %s: %v", f.Name, err)
				continue
			}

			result.Write(content)
			// Ensure there is a newline between files if not present
			if len(content) > 0 && content[len(content)-1] != '\n' {
				result.WriteByte('\n')
			}
		}
	}

	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(result.String()))
}

func main() {
	http.HandleFunc("/convert", convertHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}