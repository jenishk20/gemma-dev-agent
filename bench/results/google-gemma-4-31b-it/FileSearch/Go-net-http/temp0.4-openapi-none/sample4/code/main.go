package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

const baseDataDir = "/data"

type SearchRequest struct {
	SearchContent  *string `json:"search_content"`
	SearchFilename *string `json:"search_filename"`
	SearchDir      *string `json:"search_dir"`
}

type SearchResponse struct {
	Files []string `json:"files"`
}

func searchHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	var req SearchRequest
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	// Determine the root directory to search in
	root := baseDataDir
	if req.SearchDir != nil && *req.SearchDir != "" {
		root = filepath.Join(baseDataDir, *req.SearchDir)
	}

	// Ensure the search directory is actually within /data to prevent directory traversal
	absRoot, err := filepath.Abs(root)
	if err != nil {
		http.Error(w, "Invalid search directory", http.StatusBadRequest)
		return
	}
	if !strings.HasPrefix(absRoot, baseDataDir) {
		http.Error(w, "Invalid search directory", http.StatusBadRequest)
		return
	}

	var matchedFiles []string

	err = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // Skip files that can't be accessed
		}
		if info.IsDir() {
			return nil
		}

		match := false

		// Match by filename if specified
		if req.SearchFilename != nil && *req.SearchFilename != "" {
			if strings.Contains(info.Name(), *req.SearchFilename) {
				match = true
			}
		}

		// Match by content if specified (and not already matched by filename)
		if !match && req.SearchContent != nil && *req.SearchContent != "" {
			content, err := os.ReadFile(path)
			if err == nil {
				if strings.Contains(string(content), *req.SearchContent) {
					match = true
				}
			}
		}

		if match {
			matchedFiles = append(matchedFiles, path)
		}
		return nil
	})

	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(SearchResponse{Files: matchedFiles})
}

func main() {
	http.HandleFunc("/search", searchHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Error starting server: %s\n", err)
		os.Exit(1)
	}
}