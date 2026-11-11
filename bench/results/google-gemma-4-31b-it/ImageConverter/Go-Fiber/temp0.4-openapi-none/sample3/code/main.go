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
			return c.Status(400).JSON(fiber.Map{"error": "Failed to parse multipart form"})
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

		// Get delay
		delayStr := c.FormValue("delay")
		delay := 10 // default
		if delayStr != "" {
			if d, err := strconv.Atoi(delayStr); err == nil {
				delay = d
			}
		}

		// Get appendReverted
		appendReverted := c.FormValue("appendReverted") == "true"

		// Create a temporary directory for processing
		tempDir, err := os.MkdirTemp("", "gif-creator-*")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Internal server error creating temp dir"})
		}
		defer os.RemoveAll(tempDir)

		var inputPaths []string
		for i, fileHeader := range files {
			file, err := fileHeader.Open()
			if err != nil {
				return c.Status(400).JSON(fiber.Map{"error": fmt.Sprintf("Error opening file %d", i)})
			}
			
			filePath := filepath.Join(tempDir, fmt.Sprintf("frame_%d%s", i, filepath.Ext(fileHeader.Filename)))
			outFile, err := os.Create(filePath)
			if err != nil {
				file.Close()
				return c.Status(500).JSON(fiber.Map{"error": "Internal server error saving file"})
			}

			_, err = outFile.ReadFrom(file)
			file.Close()
			outFile.Close()
			if err != nil {
				return c.Status(500).JSON(fiber.Map{"error": "Internal server error writing file"})
			}
			inputPaths = append(inputPaths, filePath)
		}

		// Handle appendReverted logic
		var finalInputs []string
		finalInputs = append(finalInputs, inputPaths...)
		if appendReverted {
			for i := len(inputPaths) - 1; i >= 0; i-- {
				finalInputs = append(finalInputs, inputPaths[i])
			}
		}

		// Output GIF path
		outputGif := filepath.Join(tempDir, uuid.New().String()+".gif")

		// ImageMagick convert command
		// -delay is in ticks (1/100th of a second). 
		// The API specifies delay in milliseconds. 100ms = 10 ticks.
		imDelay := delay / 10
		
		args := []string{
			"-delay", strconv.Itoa(imDelay),
			"-resize", targetSize,
		}
		args = append(args, finalInputs...)
		args = append(args, outputGif)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "ImageMagick conversion failed: " + err.Error()})
		}

		// Serve the resulting GIF
		return c.SendFile(outputGif)
	})

	app.Listen(":5000")
}