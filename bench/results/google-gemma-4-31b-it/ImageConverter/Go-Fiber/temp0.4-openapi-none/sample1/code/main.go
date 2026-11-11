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
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid multipart form"})
		}

		// Get images
		files := form.File["images"]
		if len(files) == 0 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "No images provided"})
		}

		// Get targetSize
		targetSize := form.Value("targetSize")
		if targetSize == "" {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "targetSize is required"})
		}

		// Get delay
		delayStr := form.Value("delay")
		delay := 10 // default
		if delayStr != "" {
			if d, err := strconv.Atoi(delayStr); err == nil {
				delay = d
			}
		}

		// Get appendReverted
		appendRevertedStr := form.Value("appendReverted")
		appendReverted := appendRevertedStr == "true"

		// Create temporary directory for processing
		tmpDir, err := os.MkdirTemp("", "gif-creator-*")
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to create temp directory"})
		}
		defer os.RemoveAll(tmpDir)

		var inputPaths []string
		for i, file := range files {
			path := filepath.Join(tmpDir, fmt.Sprintf("img_%d", i))
			if err := c.SaveFile(file, path); err != nil {
				return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save uploaded file"})
			}
			inputPaths = append(inputPaths, path)
		}

		// Handle appendReverted: duplicate paths in reverse order
		if appendReverted {
			for i := len(inputPaths) - 1; i >= 0; i-- {
				inputPaths = append(inputPaths, inputPaths[i])
			}
		}

		// Output filename
		outputFile := filepath.Join(tmpDir, uuid.New().String()+".gif")

		// ImageMagick 'convert' command
		// -delay is in ticks (usually 1/100th of a second), so we divide ms by 10
		delayTicks := delay / 10
		if delayTicks == 0 && delay > 0 {
			delayTicks = 1
		}

		args := []string{}
		// Add delay first to apply to all frames
		args = append(args, "-delay", strconv.Itoa(delayTicks))
		// Add resize
		args = append(args, "-resize", targetSize)
		// Add all input images
		args = append(args, inputPaths...)
		// Output file
		args = append(args, outputFile)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "ImageMagick conversion failed: " + err.Error()})
		}

		// Serve the resulting GIF
		return c.SendFile(outputFile)
	})

	app.Listen("0.0.0.0:5000")
}