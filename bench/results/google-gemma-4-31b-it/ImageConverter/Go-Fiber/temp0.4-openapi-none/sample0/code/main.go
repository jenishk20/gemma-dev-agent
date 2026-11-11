package main

import (
	"fmt"
	"log"
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

		// Create a temporary directory for this request
		requestID := uuid.New().String()
		tmpDir, err := os.MkdirTemp("", "gif-creator-"+requestID)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to create temp directory"})
		}
		defer os.RemoveAll(tmpDir)

		var imagePaths []string
		for i, fileHeader := range files {
			filePath := filepath.Join(tmpDir, fmt.Sprintf("img_%d_%s", i, fileHeader.Filename))
			if err := c.SaveFile(fileHeader, filePath); err != nil {
				return c.Status(500).JSON(fiber.Map{"error": "Failed to save uploaded file"})
			}
			imagePaths = append(imagePaths, filePath)
		}

		// Handle appendReverted logic
		var finalPaths []string
		finalPaths = append(finalPaths, imagePaths...)
		if appendReverted {
			for i := len(imagePaths) - 1; i >= 0; i-- {
				finalPaths = append(finalPaths, imagePaths[i])
			}
		}

		// Output path
		outputGif := filepath.Join(tmpDir, "result.gif")

		// Build ImageMagick command: convert -delay <ms/10> -loop 0 -resize <size> <files> <output>
		// Note: ImageMagick -delay is in ticks (1/100th of a second). 
		// The schema says delay is in milliseconds. 100ms = 10 ticks.
		delayTicks := delay / 10
		
		args := []string{
			"-delay", strconv.Itoa(delayTicks),
			"-loop", "0",
			"-resize", targetSize,
		}
		args = append(args, finalPaths...)
		args = append(args, outputGif)

		cmd := exec.Command("convert", args...)
		if err := cmd.Run(); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "ImageMagick conversion failed: " + err.Error()})
		}

		// Return the GIF file
		return c.SendFile(outputGif)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}