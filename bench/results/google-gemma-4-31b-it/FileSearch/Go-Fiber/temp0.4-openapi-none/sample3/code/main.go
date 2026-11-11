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

		// Verify searchPath is still within /data to prevent directory traversal
		if !strings.HasPrefix(searchPath, baseDir) {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid search directory"})
		}

		var matchedFiles []string

		err := filepath.WalkDir(searchPath, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return nil // Skip files that cannot be accessed
			}
			if d.IsDir() {
				return nil
			}

			match := false

			// Match by filename if specified
			if req.SearchFilename != nil && *req.SearchFilename != "" {
				if strings.Contains(d.Name(), *req.SearchFilename) {
					match = true
				}
			}

			// Match by content if specified (and not already matched by filename)
			if !match && req.SearchContent != nil && *req.SearchContent != "" {
				content, err := os.ReadFile(path)
				if err == nil {
					if bytes.Contains(content, []byte(*req.SearchContent)) {
						match = true
					}
				}
			}

			// If both were provided and neither matched, or if only one was provided and it matched
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

	log.Fatal(app.Listen(":5000"))
}