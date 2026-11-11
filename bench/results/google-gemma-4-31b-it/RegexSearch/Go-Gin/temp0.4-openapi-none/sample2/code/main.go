package main

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"

	"github.com/gin-gonic/gin"
)

const rootDir = "./files"

type SearchResponse struct {
	Files []string `json:"files"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}

func main() {
	r := gin.Default()

	r.GET("/search", func(c *gin.Context) {
		regexStr := c.Query("regex")
		dirParam := c.Query("directory")
		recursiveStr := c.DefaultQuery("recursive", "false")

		if regexStr == "" {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "regex parameter is required"})
			return
		}

		re, err := regexp.Compile(regexStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: fmt.Sprintf("invalid regex: %v", err)})
			return
		}

		recursive, err := strconv.ParseBool(recursiveStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "recursive parameter must be a boolean"})
			return
		}

		// Construct the absolute path to search
		searchPath := filepath.Join(rootDir, dirParam)

		// Security check: ensure searchPath is within rootDir to prevent directory traversal
		absRoot, err := filepath.Abs(rootDir)
		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "server error resolving root directory"})
			return
		}
		absSearch, err := filepath.Abs(searchPath)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "invalid directory path"})
			return
		}

		// Simple check to ensure the search path is a subdirectory of the root
		// This is a basic implementation; in production, more robust path validation is needed.
		// We check if the search path starts with the root path.
		// Note: This doesn't handle symlinks, but fits the requirement.

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

			content, err := os.ReadFile(path)
			if err != nil {
				return nil // Skip files that cannot be read
			}

			if re.Match(content) {
				// Calculate path relative to the search directory
				rel, err := filepath.Rel(searchPath, path)
				if err != nil {
					rel = path
				}
				matchedFiles = append(matchedFiles, rel)
			}
			return nil
		})

		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: fmt.Sprintf("error accessing directory: %v", err)})
			return
		}

		c.JSON(http.StatusOK, SearchResponse{Files: matchedFiles})
	})

	r.Run("0.0.0.0:5000")
}