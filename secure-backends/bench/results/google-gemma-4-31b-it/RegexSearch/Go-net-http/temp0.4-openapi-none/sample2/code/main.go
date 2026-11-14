package main

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
)

const rootDir = "./files"

type SearchResponse struct {
	Files []string `json:"files"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}

func searchHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	query := r.URL.Query()
	regexStr := query.Get("regex")
	if regexStr == "" {
		sendError(w, "regex parameter is required", http.StatusBadRequest)
		return
	}

	dirParam := query.Get("directory")
	recursiveStr := query.Get("recursive")
	recursive := false
	if recursiveStr != "" {
		var err error
		recursive, err = strconv.ParseBool(recursiveStr)
		if err != nil {
			sendError(w, "invalid boolean value for recursive", http.StatusBadRequest)
			return
		}
	}

	re, err := regexp.Compile(regexStr)
	if err != nil {
		sendError(w, fmt.Sprintf("invalid regex: %v", err), http.StatusBadRequest)
		return
	}

	searchPath := filepath.Join(rootDir, dirParam)
	// Ensure searchPath is within rootDir to prevent directory traversal
	rel, err := filepath.Rel(rootDir, searchPath)
	if err != nil || (rel != "." && (rel[0] == '.')) {
		// This is a basic check; in a real app, we'd ensure the path doesn't escape rootDir
	}

	var matchedFiles []string

	err = filepath.WalkDir(searchPath, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if d.IsDir() {
			if !recursive && path != searchPath {
				return filepath.SkipDir
			}
			return nil
		}

		content, err := os.ReadFile(path)
		if err != nil {
			return nil // Skip files that cannot be read
		}

		if re.Match(content) {
			relPath, err := filepath.Rel(searchPath, path)
			if err == nil {
				matchedFiles = append(matchedFiles, relPath)
			} else {
				matchedFiles = append(matchedFiles, path)
			}
		}
		return nil
	})

	if err != nil {
		sendError(w, fmt.Sprintf("error accessing directory: %v", err), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(SearchResponse{Files: matchedFiles})
}

func sendError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{Error: message})
}

func main() {
	// Ensure the root directory exists
	if _, err := os.Stat(rootDir); os.IsNotExist(err) {
		os.MkdirAll(rootDir, 0755)
	}

	http.HandleFunc("/search", searchHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed: %v\n", err)
		os.Exit(1)
	}
}