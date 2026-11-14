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

	// Parse the multipart form, limiting the upload size to 10MB
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Could not parse multipart form", http.StatusBadRequest)
		return
	}

	// Retrieve the file from the form data
	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Invalid input: file field is missing", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// We need a ReaderAt for zip.NewReader, so we read the file into memory
	// For a production app, we might save this to a temporary file.
	data, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, "Error reading file", http.StatusInternalServerError)
		return
	}

	// Create a reader for the zip archive
	reader := zip.NewReader(strings.NewReader(string(data)), int64(len(data)))

	var result strings.Builder

	// Iterate through the files in the zip archive
	for _, f := range reader.File {
		// We only process files that look like text files (simple check by extension)
		// or we can try to read everything and let the user handle non-text content.
		// The prompt asks for "contents of all text files".
		if isTextFile(f.Name) {
			rc, err := f.Open()
			if err != nil {
				continue // Skip files that cannot be opened
			}

			content, err := io.ReadAll(rc)
			rc.Close()
			if err != nil {
				continue
			}

			result.Write(content)
			result.WriteString("\n") // Add newline between files
		}
	}

	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, result.String())
}

// isTextFile provides a basic check to see if a file should be treated as text
func isTextFile(name string) bool {
	// Simple check: if it's a directory, skip it.
	if strings.HasSuffix(name, "/") {
		return false
	}
	// In a real scenario, we'd check MIME types or a list of extensions.
	// For this implementation, we assume files without binary-looking extensions are text.
	// But to be safe and follow "text files in the zip", we check common text extensions.
	extensions := []string{".txt", ".md", ".json", ".xml", ".html", ".css", ".js", ".go", ".py", ".c", ".cpp", ".h"}
	for _, ext := range extensions {
		if strings.HasSuffix(strings.ToLower(name), ext) {
			return true
		}
	}
	// If it has no extension, we'll treat it as text as well.
	if !strings.Contains(name, ".") {
		return true
	}
	return false
}

func main() {
	http.HandleFunc("/convert", convertHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	err := http.ListenAndServe("0.0.0.0:5000", nil)
	if err != nil {
		fmt.Printf("Error starting server: %s\n", err)
	}
}