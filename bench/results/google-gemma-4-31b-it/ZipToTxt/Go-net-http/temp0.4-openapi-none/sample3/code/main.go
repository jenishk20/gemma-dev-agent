package main

import (
	"archive/zip"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// convertHandler handles the POST /convert endpoint
func convertHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse the multipart form to get the file
	// 10MB max memory for the file upload
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Could not parse multipart form", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Invalid input: file field is required", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// We need a ReaderAt for zip.NewReader. 
	// Since we have a multipart file, we can't use it directly as ReaderAt.
	// We read it into a byte slice.
	content, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, "Error reading file", http.StatusInternalServerError)
		return
	}

	// Create a reader for the zip archive
	reader, err := zip.NewReader(strings.NewReader(string(content)), int64(len(content)))
	if err != nil {
		// If it's not a valid zip, we treat it as a 400 Bad Request
		http.Error(w, "Invalid zip file", http.StatusBadRequest)
		return
	}

	var result strings.Builder

	// Iterate through the files in the zip archive
	for _, f := range reader.File {
		// We only process files that are not directories
		if f.FileInfo().IsDir() {
			continue
		}

		rc, err := f.Open()
		if err != nil {
			continue // Skip files that cannot be opened
		}

		// Read the content of the file
		buf := make([]byte, 1024)
		for {
			n, err := rc.Read(buf)
			if n > 0 {
				result.Write(buf[:n])
			}
			if err == io.EOF {
				break
			}
			if err != nil {
				rc.Close()
				http.Error(w, "Error reading zip entry", http.StatusInternalServerError)
				return
			}
		}
		rc.Close()
		
		// Add a newline between files to ensure they are separated
		result.WriteString("\n")
	}

	w.Header().Set("Content-Type", "text/plain")
	fmt.Fprint(w, result.String())
}

func main() {
	http.HandleFunc("/convert", convertHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	err := http.ListenAndServe("0.0.0.0:5000", nil)
	if err != nil {
		fmt.Printf("Server failed: %s\n", err)
	}
}