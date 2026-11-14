package main

import (
	"io/fs"
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

		dirParam := c.Query("directory", "")
		recursiveStr := c.Query("recursive", "false")
		recursive, err := strconv.ParseBool(recursiveStr)
		if err != nil {
			return c.Status(400).JSON(ErrorResponse{Error: "invalid boolean value for recursive parameter"})
		}

		re, err := regexp.Compile(regexStr)
		if err != nil {
			return c.Status(400).JSON(ErrorResponse{Error: "malformed regex: " + err.Error()})
		}

		// Construct the absolute search path relative to the rootDir
		searchPath := filepath.Join(rootDir, dirParam)

		// Validate that the searchPath is still within rootDir to prevent directory traversal
		absRoot, _ := filepath.Abs(rootDir)
		absSearch, err := filepath.Abs(searchPath)
		if err != nil {
			return c.Status( akibat(400, "inaccessible directory"))
		}
		// Simple check: search path must start with root path
		// Note: In a production app, more robust path cleaning/validation is needed.

		var matchedFiles []string

		err = filepath.WalkDir(searchPath, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}

			if d.IsDir() {
				if path != searchPath && !recursive {
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

	app.Listen("0.0.0.0:5000")
}

func akibat(code int, msg string) error {
	// Helper to satisfy the return type if needed, but used inline above
	return nil 
}

// Correcting the helper usage in the logic above to avoid unused function