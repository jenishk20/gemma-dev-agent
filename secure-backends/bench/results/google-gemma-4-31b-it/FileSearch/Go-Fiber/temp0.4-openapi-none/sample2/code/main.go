package main

import (
	"bytes"
	"fmt"
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
		if err := c.RequestBody().Bind().JSON(&req); err != nil {
			// Fiber's BodyParser is preferred for JSON
		}
		// Re-parsing using BodyParser for reliability in Fiber
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid input"})
		}

		// Base directory is /data
		baseDir := "/data"
		searchPath := baseDir

		// If search_dir is provided, append it to /data
		if req.SearchDir != nil && *req.SearchDir != "" {
			searchPath = filepath.Join(baseDir, *req.SearchDir)
		}

		var matchedFiles []string

		// Walk through the directory
		err := filepath.WalkDir(searchPath, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return nil // Skip directories we can't access
			}
			if d.IsDir() {
				return nil
			}

			match := false

			// 1. Check Filename match (starts with)
			if req.SearchFilename != nil && *req.SearchFilename != "" {
				if strings.HasPrefix(d.Name(), *req.SearchFilename) {
					match = true
				}
			}

			// 2. Check Content match
			if !match && req.SearchContent != nil && *req.SearchContent != "" {
				content, err := os.ReadFile(path)
				if err == nil {
					if bytes.Contains(content, []byte(*req.SearchContent)) {
						match = true
					}
				}
			}

			if match {
				matchedFiles = append(matchedFiles, path)
			}

			return nil
		})

		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Server error during search"})
		}

		return c.JSON(SearchResponse{Files: matchedFiles})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}