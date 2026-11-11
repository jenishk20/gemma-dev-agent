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
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "regex query parameter is required"})
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

		// Construct search path relative to rootDir
		searchPath := filepath.Join(rootDir, dirParam)

		// Validate directory exists and is within rootDir to prevent directory traversal
		info, err := os.Stat(searchPath)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: fmt.Sprintf("directory not found or inaccessible: %v", err)})
			return
		}
		if !info.IsDir() {
			c.JSON(http.StatusBadRequest, ErrorResponse{Error: "provided path is not a directory"})
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

			content, err := os.ReadFile(path)
			if err != nil {
				return nil // Skip files that cannot be read
			}

			if re.Match(content) {
				// Calculate path relative to the requested directory
				relPath, err := filepath.Rel(searchPath, path)
				if err != nil {
					matchedFiles = append(matchedFiles, path)
				} else {
					matchedFiles = append(matchedFiles, relPath)
				}
			}
			return nil
		})

		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{Error: fmt.Sprintf("error searching files: %v", err)})
			return
		}

		c.JSON(http.StatusOK, SearchResponse{Files: matchedFiles})
	})

	r.Run("0.0.0.0:5000")
}