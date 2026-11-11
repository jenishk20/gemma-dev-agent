package main

import (
	"archive/zip"
	"fmt"
	"io"
	"net/http"
	"strings"
)

func convertHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Limit upload size to 10MB to prevent DoS
	r.Body = http.MaxBytesReader(w, r.Body, 10<<20)

	// Parse multipart form
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Invalid input: could not parse form", http.StatusBadRequest)
		return
	}

	file, _, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Invalid input: file field missing", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Since archive/zip requires a ReaderAt, we need to read the file into a buffer
	// or save it to a temporary file. For a simple webapp, we'll use a byte slice.
	data, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, "Internal server error reading file", http.StatusInternalServerError)
		return
	}

	// Create a reader from the byte slice
	reader := strings.NewReader(string(data))
	zipReader, err := zip.NewReader(reader, int64(len(data)))
	if err != nil {
		http.Error(w, "Invalid zip file", http.StatusBadRequest)
		return
	}

	var result strings.Builder

	for _, f := range zipReader.File {
		// Only process files (not directories)
		if f.FileInfo().IsDir() {
			continue
		}

		// Open the file within the zip
		rc, err := f.Open()
		if err != nil {
			continue // Skip files that cannot be opened
		}

		// Read content
		content, err := io.ReadAll(rc)
		rc.Close()
		if err != nil {
			continue // Skip files that cannot be read
		}

		// Append content to the result
		result.Write(content)
		result.WriteString("\n") // Add newline between files
	}

	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(result.String()))
}

func main() {
	http.HandleFunc("/convert", convertHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	err := http.ListenAndServe("0.0.0.0:5000", nil)
	if err != nil {
		fmt.Printf("Error starting server: %s\n", err)
	}
}