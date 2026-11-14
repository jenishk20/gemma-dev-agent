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

const baseDataDir = "/data"

func main() {
	r := gin.Default()

	r.POST("/search", func(c *gin.Context) {
		var req SearchRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		// Determine the root directory for search
		root := baseDataDir
		if req.SearchDir != nil && *req.SearchDir != "" {
			root = filepath.Join(baseDataDir, *req.SearchDir)
		}

		var matchedFiles []string

		err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil // Skip files that cause errors
			}
			if info.IsDir() {
				return nil
			}

			// Check filename match
			if req.SearchFilename != nil && *req.SearchFilename != "" {
				if strings.Contains(info.Name(), *req.SearchFilename) {
					matchedFiles = append(matchedFiles, path)
					return nil
				}
			}

			// Check content match
			if req.SearchContent != nil && *req.SearchContent != "" {
				if containsContent(path, *req.SearchContent) {
					matchedFiles = append(matchedFiles, path)
					return nil
				}
			}

			return nil
		})

		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Server error during search"})
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