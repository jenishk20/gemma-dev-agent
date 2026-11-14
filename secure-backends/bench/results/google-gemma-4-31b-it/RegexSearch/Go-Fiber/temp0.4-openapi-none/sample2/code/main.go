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
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Error: "Query parameter 'regex' is required",
			})
		}

		re, err := regexp.Compile(regexStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Error: fmt.Sprintf("Invalid regex: %v", err),
			})
		}

		dirParam := c.Query("directory", "")
		recursiveParam := c.Query("recursive", "false")
		recursive, err := strconv.ParseBool(recursiveParam)
		if err != nil {
			recursive = false
		}

		// Construct the absolute path to search
		searchPath := filepath.Join(rootDir, dirParam)

		// Verify the directory exists and is actually a directory
		info, err := os.Stat(searchPath)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Error: fmt.Sprintf("Directory not found or inaccessible: %v", err),
			})
		}
		if !info.IsDir() {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Error: "The specified path is not a directory",
			})
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
					matchedFiles = append(matchedFiles, path)
				} else {
					matchedFiles = append(matchedFiles, relPath)
				}
			}

			return nil
		})

		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{
				Error: fmt.Sprintf("Error searching files: %v", err),
			})
		}

		return c.JSON(SearchResponse{Files: matchedFiles})
	})

	app.Listen("0.0.0.0:5000")
}