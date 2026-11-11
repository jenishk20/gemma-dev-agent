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

		// Create a temporary directory for processing
		tempDir, err := os.MkdirTemp("", "gif-creator-")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to create temp directory"})
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, file := range files {
			path := filepath.Join(tempDir, fmt.Sprintf("img_%d_%s", i, file.Filename))
			if err := c.SaveFile(file, path); err != nil {
				return c.Status(500).JSON(fiber.Map{"error": "Failed to save uploaded image"})
			}
			inputPaths = append(inputPaths, path)
		}

		// Handle appendReverted logic
		var finalInputs []string
		if appendReverted {
			finalInputs = append(finalInputs, inputPaths...)
			for i := len(inputPaths) - 1; i >= 0; i-- {
				finalInputs = append(finalInputs, inputPaths[i])
			}
		} else {
			finalInputs = inputPaths
		}

		// Output path
		outputFileName := uuid.New().String() + ".gif"
		outputPath := filepath.Join(tempDir, outputFileName)

		// ImageMagick command: convert -delay [ms/10] -loop 0 [inputs] -resize [size] [output]
		// Note: ImageMagick -delay is in ticks (1/100th of a second), so ms / 10
		delayTicks := strconv.Itoa(delay / 10)
		
		args := []string{"-delay", delayTicks, "-loop", "0"}
		args = append(args, finalInputs...)
		args = append(args, "-resize", targetSize)
		args = append(args, outputPath)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "ImageMagick conversion failed: " + err.Error()})
		}

		// Serve the resulting GIF
		return c.SendFile(outputPath)
	})

	app.Listen("0.0.0.0:5000")
}