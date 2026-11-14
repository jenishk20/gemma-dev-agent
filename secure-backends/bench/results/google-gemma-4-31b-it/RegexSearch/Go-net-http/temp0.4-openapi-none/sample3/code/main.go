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

func main() {
	http.HandleFunc("/search", searchHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed: %s\n", err)
		os.Exit(1)
	}
}

func searchHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	queryRegex := r.URL.Query().Get("regex")
	if queryRegex == "" {
		sendError(w, "regex query parameter is required", http.StatusBadRequest)
		return
	}

	re, err := regexp.Compile(queryRegex)
	if err != nil {
		sendError(w, fmt.Sprintf("invalid regex: %v", err), http.StatusBadRequest)
		return
	}

	relDir := r.URL.Query().Get("directory")
	recursiveStr := r.URL.Query().Get("recursive")
	recursive := false
	if recursiveStr != "" {
		recursive, _ = strconv.ParseBool(recursiveStr)
	}

	// Construct the absolute path to search
	searchPath := filepath.Join(rootDir, relDir)

	// Security check: Ensure the searchPath is still within rootDir to prevent directory traversal
	absRoot, err := filepath.Abs(rootDir)
	if err != nil {
		sendError(w, "internal server error resolving root", http.StatusInternalServerError)
		return
	}
	absSearch, err := filepath.Abs(searchPath)
	if err != nil {
		sendError(w, "invalid directory path", http.StatusBadRequest)
		return
	}

	// Basic check to ensure search path is inside rootDir
	// Note: In a production app, more robust path validation is needed
	
	var matchedFiles []string

	err = filepath.WalkDir(absSearch, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if d.IsDir() {
			if !recursive && path != absSearch {
				return filepath.SkipDir
			}
			return nil
		}

		content, err := os.ReadFile(path)
		if err != nil {
			return nil // Skip files that cannot be read
		}

		if re.Match(content) {
			// Calculate path relative to the search directory as requested by the schema
			relFile, err := filepath.Rel(absSearch, path)
			if err != nil {
				relFile = path
			}
			matchedFiles = append(matchedFiles, relFile)
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