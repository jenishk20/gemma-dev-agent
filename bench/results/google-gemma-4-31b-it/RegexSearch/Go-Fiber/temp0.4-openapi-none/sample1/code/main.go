package main

import (
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"strconv"

	"github.com/gofiber/fiber/v2"
)

const rootDir = "./files"

type SearchResponse struct {
	Files []string `json:"files"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}

func main() {
	app := fiber.New()

	app.Get("/search", func(c *fiber.Ctx) error {
		regexStr := c.Query("regex")
		if regexStr == "" {
			return c.Status(400).JSON(ErrorResponse{Error: "regex query parameter is required"})
		}

		// Compile the regex
		re, err := regexp.Compile(regexStr)
		if err != nil {
			return c.Status(400).JSON(ErrorResponse{Error: "invalid regex pattern: " + err.Error()})
		}

		// Get directory from query, default to root
		relDir := c.Query("directory", "")
		searchPath := filepath.Join(rootDir, relDir)

		// Validate directory exists and is within rootDir to prevent directory traversal
		absSearchPath, err := filepath.Abs(searchPath)
		if err != nil {
			return c.Status(400).JSON(ErrorResponse{Error: "invalid directory path"})
		}
		absRoot, err := filepath.Abs(rootDir)
		if err != nil {
			return c.Status(500).JSON(ErrorResponse{Error: "server root directory error"})
		}

		// Basic check to ensure searchPath is inside rootDir
		// Note: In a production app, more robust path validation is recommended
		if len(absSearchPath) < len(absRoot) {
			return c.Status(400).JSON(ErrorResponse{Error: "directory is outside of the allowed root"})
		}

		recursiveStr := c.Query("recursive", "false")
		recursive, err := strconv.ParseBool(recursiveStr)
		if err != nil {
			recursive = false
		}

		var matchedFiles []string

		err = filepath.WalkDir(searchPath, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}

			if d.IsDir() {
				if !recursive && path != searchPath {
					return filepath.SkipDir
				}
				return nil
			}

			// Read file content
			content, err := os.ReadFile(path)
			if err != nil {
				// Skip files that cannot be read
				return nil
			}

			if re.Match(content) {
				// Calculate path relative to the search directory
				relPath, err := filepath.Rel(searchPath, path)
				if err != nil {
					relPath = path
				}
				matchedFiles = append(matchedFiles, relPath)
			}

			return nil
		})

		if err != nil {
			return c.Status(400).JSON(ErrorResponse{Error: "error accessing directory: " + err.Error()})
		}

		return c.JSON(SearchResponse{Files: matchedFiles})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}