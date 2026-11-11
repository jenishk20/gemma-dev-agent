package main

import (
	"bytes"
	"io/fs"
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
		err := filepath.WalkDir(searchPath, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return nil // Skip directories/files that can't be accessed
			}
			if d.IsDir() {
				return nil
			}

			// Check filename match
			if req.SearchFilename != nil && *req.SearchFilename != "" {
				if strings.Contains(d.Name(), *req.SearchFilename) {
					matchedFiles = append(matchedFiles, path)
					return nil
				}
			}

			// Check content match
			if req.SearchContent != nil && *req.SearchContent != "" {
				content, err := os.ReadFile(path)
				if err == nil {
					if bytes.Contains(content, []byte(*req.SearchContent)) {
						// Avoid duplicates if filename already matched
						exists := false
						for _, f := range matchedFiles {
							if f == path {
								exists = true
								break
							}
						}
						if !exists {
							matchedFiles = append(matchedFiles, path)
						}
					}
				}
			}

			return nil
		})

		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Error accessing search directory"})
		}

		return c.JSON(SearchResponse{Files: matchedFiles})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}