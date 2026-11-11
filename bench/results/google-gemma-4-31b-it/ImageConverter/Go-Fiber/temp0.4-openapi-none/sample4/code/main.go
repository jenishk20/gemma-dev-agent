package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

func main() {
	app := fiber.New()

	app.Post("/create-gif", func(c *fiber.Ctx) error {
		// Parse multipart form
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid multipart form"})
		}

		// Get images
		files := form.File["images"]
		if len(files) == 0 {
			return c.Status(400).JSON(fiber.Map{"error": "No images provided"})
		}

		// Get targetSize
		targetSize := c.FormValue("targetSize")
		if targetSize == "" {
			return c.Status(400).JSON(fiber.Map{"error": "targetSize is required"})
		}

		// Get delay (default 10)
		delayStr := c.FormValue("delay")
		delay := 10
		if delayStr != "" {
			if d, err := strconv.Atoi(delayStr); err == nil {
				delay = d
			}
		}

		// Get appendReverted (default false)
		appendReverted := c.FormValue("appendReverted") == "true"

		// Create temporary directory for processing
		tempDir, err := os.MkdirTemp("", "gif-creator-")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to create temp directory"})
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			filePath := filepath.Join(tempDir, fmt.Sprintf("img_%d_%s", i, fileHeader.Filename))
			if err := c.SaveFile(fileHeader, filePath); err != nil {
				return c.Status(500).JSON(fiber.Map{"error": "Failed to save uploaded image"})
			}
			inputPaths = append(inputPaths, filePath)
		}

		// Handle appendReverted: duplicate and reverse the list
		if appendReverted {
			for i := len(inputPaths) - 2; i >= 0; i-- {
				// We don't need to save new files, just refer to existing ones in reverse order
				inputPaths = append(inputPaths, inputPaths[i])
			}
		}

		// Output filename
		outputFile := filepath.Join(tempDir, uuid.New().String()+".gif")

		// Build ImageMagick command
		// convert -delay <delay/100> -size <targetSize> -loop 0 <inputs> <output>
		// Note: ImageMagick delay is in ticks (1/100th of a second). 
		// The schema asks for milliseconds. 100ms = 10 ticks.
		imDelay := delay / 10
		args := []string{
			"-delay", strconv.Itoa(imDelay),
			"-size", targetSize,
			"-loop", "0",
		}
		args = append(args, inputPaths...)
		args = append(args, outputFile)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "ImageMagick conversion failed: " + err.Error()})
		}

		// Serve the resulting GIF
		return c.SendFile(outputFile)
	})

	app.Listen(":5000")
}