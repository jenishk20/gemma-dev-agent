package main

import (
	"bufio"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
)

type SearchRequest struct {
	SearchContent  *string `json:"search_content"`
	SearchFilename *string `json:"search_filename"`
	SearchDir      *string `json:"search_dir"`
}

type SearchResponse struct {
	Files []string `json:"files"`
}

func main() {
	r := gin.Default()

	r.POST("/search", func(c *gin.Context) {
		var req SearchRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		// Base directory is /data
		baseDir := "/data"
		searchPath := baseDir

		// If search_dir is provided, append it to baseDir
		if req.SearchDir != nil && *req.SearchDir != "" {
			searchPath = filepath.Join(baseDir, *req.SearchDir)
		}

		var matchedFiles []string

		err := filepath.Walk(searchPath, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil // Skip files/dirs that cannot be accessed
			}
			if info.IsDir() {
				return nil
			}

			match := false

			// Match by filename if provided
			if req.SearchFilename != nil && *req.SearchFilename != "" {
				if strings.Contains(info.Name(), *req.SearchFilename) {
					match = true
				}
			}

			// Match by content if provided (and not already matched by filename)
			if !match && req.SearchContent != nil && *req.SearchContent != "" {
				if containsContent(path, *req.SearchContent) {
					match = true
				}
			}

			if match {
				matchedFiles = append(matchedFiles, path)
			}

			return nil
		})

		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Error searching files"})
			return
		}

		c.JSON(http.StatusOK, SearchResponse{Files: matchedFiles})
	})

	r.Run("0.0.0.0:5000")
}

func containsContent(filePath string, content string) bool {
	file, err := os.Open(filePath)
	if err != nil {
		return false
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if strings.Contains(scanner.Text(), content) {
			return true
		}
	}
	return false
}