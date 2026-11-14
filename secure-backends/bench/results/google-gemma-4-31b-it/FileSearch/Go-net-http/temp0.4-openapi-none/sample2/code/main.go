package main

import (
	"encoding/json"
	"fmt"
	"io/fs"
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
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req SearchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	// Determine the starting directory
	searchPath := baseDataDir
	if req.SearchDir != nil && *req.SearchDir != "" {
		searchPath = filepath.Join(baseDataDir, *req.SearchDir)
	}

	// Validate that the search path is still within /data to prevent directory traversal
	absSearchPath, err := filepath.Abs(searchPath)
	if err != nil {
		http.Error(w, "Invalid search directory", http.StatusBadRequest)
		return
	}
	if !strings.HasPrefix(absSearchPath, baseDataDir) {
		http.Error(w, "Invalid search directory", http.StatusBadRequest)
		return
	}

	var matchedFiles []string

	err = filepath.WalkDir(absSearchPath, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}

		match := false

		// Check filename match
		if req.SearchFilename != nil && *req.SearchFilename != "" {
			if strings.Contains(d.Name(), *req.SearchFilename) {
				match = true
			}
		}

		// Check content match
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
		http.Error(w, fmt.Sprintf("Error searching files: %v", err), http.StatusInternalServerError)
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