package main

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"log"
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
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	// Determine the starting directory
	searchPath := baseDataDir
	if req.SearchDir != nil && *req.SearchDir != "" {
		searchPath = filepath.Join(baseDataDir, *req.SearchDir)
	}

	// Ensure the search path is still within /data to prevent directory traversal
	absSearchPath, err := filepath.Abs(searchPath)
	if err != nil || !strings.HasPrefix(absSearchPath, baseDataDir) {
		// If the path is invalid or escapes /data, we default to baseDataDir or return 400
		// For this implementation, we'll treat it as a bad request if it escapes the root
		if err != nil || !strings.HasPrefix(absSearchPath, baseDataDir) {
			http.Error(w, "Invalid search directory", http.StatusBadRequest)
			return
		}
	}

	var matchedFiles []string

	err = filepath.WalkDir(searchPath, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}

		// Filter by filename if specified
		if req.SearchFilename != nil && *req.SearchFilename != "" {
			if !strings.Contains(d.Name(), *req.SearchFilename) {
				return nil
			}
		}

		// Filter by content if specified
		if req.SearchContent != nil && *req.SearchContent != "" {
			content, err := os.ReadFile(path)
			if err != nil {
				return nil // Skip files that cannot be read
			}
			if !strings.Contains(string(content), *req.SearchContent) {
				return nil
			}
		}

		matchedFiles = append(matchedFiles, path)
		return nil
	})

	if err != nil {
		http.Error(w, "Error searching files", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(SearchResponse{Files: matchedFiles})
}

func main() {
	http.HandleFunc("/search", searchHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}