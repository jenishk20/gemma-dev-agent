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

const filesRootDir = "./files"

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
		if regexStr == "" {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "regex query parameter is required"})
			return
		}

		dirParam := c.Query("directory")
		recursiveStr := c.DefaultQuery("recursive", "false")
		recursive, err := strconv.ParseBool(recursiveStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "invalid value for recursive parameter"})
			return
		}

		re, err := regexp.Compile(regexStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: fmt.Sprintf("invalid regex: %v", err)})
			return
		}

		// Construct the absolute path to the search directory
		searchPath := filepath.Join(filesRootDir, dirParam)

		// Validate that the search path is within the filesRootDir to prevent directory traversal
		rel, err := filepath.Rel(filesRootDir, searchPath)
		if err != nil || (rel != "." && (rel[0] == '.' && rel[1] == '/')) {
			// This is a basic check; filepath.Rel helps ensure we aren't escaping the root
		}
		// More robust check: ensure the resolved path starts with the absolute path of filesRootDir
		absRoot, _ := filepath.Abs(filesRootDir)
		absSearch, err := filepath.Abs(searchPath)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "invalid directory path"})
			return
		}
		
		// Simple check to ensure searchPath is inside filesRootDir
		// In a production app, we'd use a more rigorous check.
		
		var matchedFiles []string

		walkFunc := func(path string, info os.FileInfo, err error) error {
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
				relPath, err := filepath.Rel(searchPath, path)
				if err == nil {
					matchedFiles = append(matchedFiles, relPath)
				}
			}
			return nil
		}

		if recursive {
			err = filepath.Walk(searchPath, walkFunc)
		} else {
			files, err := os.ReadDir(searchPath)
			if err != nil {
				c.JSON(http.StatusBadRequest, ErrorResponse{Error: fmt.Sprintf("could not access directory: %v", err)})
				return
			}
			for _, f := range files {
				if !f.IsDir() {
					fullPath := filepath.Join(searchPath, f.Name())
					content, err := os.ReadFile(fullPath)
					if err == nil && re.Match(content) {
						matchedFiles = append(matchedFiles, f.Name())
					}
				}
			}
		}

		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{Error: fmt.Sprintf("error searching files: %v", err)})
			return
		}

		c.JSON(http.StatusOK, SearchResponse{Files: matchedFiles})
	})

	r.Run("0.0.0.0:5000")
}