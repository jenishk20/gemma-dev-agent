package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
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
	
	// Ensure the search path is within the rootDir to prevent directory traversal
	absRoot, _ := filepath.Abs(rootDir)
	absSearch, err := filepath.Abs(searchPath)
	if err != nil || !filepath.HasPrefix(absSearch, absRoot) {
		sendError(w, "invalid directory path", http.StatusBadRequest)
		return
	}

	var matchedFiles []string

	err = filepath.Walk(searchPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			if !recursive && path != searchPath {
				return filepath.SkipDir
			}
			return nil
		}

		content, err := ioutil.ReadFile(path)
		if err != nil {
			return nil // Skip files that cannot be read
		}

		if re.Match(content) {
			relPath, err := filepath.Rel(searchPath, path)
			if err != nil {
				relPath = path
			}
			matchedFiles = append(matchedFiles, relPath)
		}
		return nil
	})

	if err != nil {
		sendError(w, fmt.Sprintf("error searching files: %v", err), http.StatusInternalServerError)
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
	// Ensure root directory exists
	if _, err := os.Stat(rootDir); os.IsNotExist(err) {
		os.MkdirAll(rootDir, 0755)
	}

	http.HandleFunc("/search", searchHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Server failed: %v\n", err)
	}
}