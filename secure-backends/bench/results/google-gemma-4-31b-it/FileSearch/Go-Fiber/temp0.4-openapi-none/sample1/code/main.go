package main

import (
	"bufio"
	"fmt"
	"log"
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

const BaseDataDir = "/data"

func main() {
	app := fiber.New()

	app.Post("/search", func(c *fiber.Ctx) error {
		var req SearchRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		// Determine the root directory to search in
		root := BaseDataDir
		if req.SearchDir != nil {
			// Ensure the search directory is within /data to prevent directory traversal
			cleanDir := filepath.Clean(*req.SearchDir)
			if !strings.HasPrefix(cleanDir, "/") {
				root = filepath.Join(BaseDataDir, cleanDir)
			} else {
				// If it's an absolute path, we still force it to be relative to /data for security
				// or validate it starts with /data. Here we treat it as relative to /data.
				root = filepath.Join(BaseDataDir, strings.TrimPrefix(cleanDir, "/"))
			}
		}

		var matchedFiles []string

		err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil // Skip files/dirs that cannot be accessed
			}
			if info.IsDir() {
				return nil
			}

			match := false

			// Check filename match
			if req.SearchFilename != nil && *req.SearchFilename != "" {
				if strings.Contains(info.Name(), *req.SearchFilename) {
					match = true
				}
			}

			// Check content match
			if !match && req.SearchContent != nil && *req.SearchContent != "" {
				if fileContains(path, *req.SearchContent) {
					match = true
				}
			}

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

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

func fileContains(filePath string, content string) bool {
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