package main

import (
	"fmt"
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
			return c.Status(400).JSON(ErrorResponse{Error: "invalid value for recursive parameter"})
		}

		re, err := regexp.Compile(regexStr)
		if err != nil {
			return c.Status(400).JSON(ErrorResponse{Error: fmt.Sprintf("invalid regex: %v", err)})
		}

		// Construct the absolute search path
		searchPath := filepath.Join(rootDir, dirParam)

		// Verify the directory exists and is within the rootDir to prevent directory traversal
		info, err := os.Stat(searchPath)
		if err != nil {
			return c.Status(400).JSON(ErrorResponse{Error: "directory not found or inaccessible"})
		}
		if !info.IsDir() {
			return c.Status(400).JSON(ErrorResponse{Error: "specified path is not a directory"})
		}

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
				rel, err := filepath.Rel(searchPath, path)
				if err == nil {
					matchedFiles = append(matchedFiles, rel)
				}
			}

			return nil
		})

		if err != nil {
			return c.Status(500).JSON(ErrorResponse{Error: fmt.Sprintf("internal server error: %v", err)})
		}

		return c.JSON(SearchResponse{Files: matchedFiles})
	})

	app.Listen("0.0.0.0:5000")
}