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
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Error: "Query parameter 'regex' is required",
			})
		}

		re, err := regexp.Compile(regexStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Error: "Invalid regex pattern: " + err.Error(),
			})
		}

		subDir := c.Query("directory", "")
		recursiveStr := c.Query("recursive", "false")
		recursive, err := strconv.ParseBool(recursiveStr)
		if err != nil {
			recursive = false
		}

		searchPath := filepath.Join(rootDir, subDir)

		// Validate that the search path is within the rootDir to prevent directory traversal
		absRoot, _ := filepath.Abs(rootDir)
		absSearch, err := filepath.Abs(searchPath)
		if err != nil || absSearch[:len(absRoot)] != absRoot {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Error: "Invalid or inaccessible directory",
			})
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
			return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{
				Error: "Internal server error: " + err.Error(),
			})
		}

		return c.JSON(SearchResponse{Files: matchedFiles})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}