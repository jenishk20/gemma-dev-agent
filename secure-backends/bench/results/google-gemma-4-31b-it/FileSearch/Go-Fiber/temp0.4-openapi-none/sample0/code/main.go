package main

import (
	"bufio"
	"os"
	"path/filepath"
	"strings"

	"github.com/gofiber/fiber/v2"
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
	app := fiber.New()

	app.Post("/search", func(c *fiber.Ctx) error {
		var req SearchRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		// Base directory is /data
		baseDir := "/data"
		searchPath := baseDir

		// If search_dir is provided, append it to baseDir
		if req.SearchDir != nil && *req.SearchDir != "" {
			searchPath = filepath.Join(baseDir, *req.SearchDir)
		}

		var matchedFiles []string

		// Walk through the directory
		err := filepath.Walk(searchPath, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil // Skip files that cannot be accessed
			}
			if info.IsDir() {
				return nil
			}

			match := false

			// 1. Check filename match
			if req.SearchFilename != nil && *req.SearchFilename != "" {
				if strings.Contains(info.Name(), *req.SearchFilename) {
					match = true
				}
			}

			// 2. Check content match (if not already matched by filename or if filename wasn't provided)
			if !match && req.SearchContent != nil && *req.SearchContent != "" {
				if fileContainsContent(path, *req.SearchContent) {
					match = true
				}
			}

			// If either condition is met (or both), add to list
			// Note: The schema says "contain the specified content OR match the filename"
			if match {
				matchedFiles = append(matchedFiles, path)
			}

			return nil
		})

		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Internal server error during file search"})
		}

		return c.JSON(SearchResponse{Files: matchedFiles})
	})

	app.Listen(":5000")
}

func fileContainsContent(filePath string, content string) bool {
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