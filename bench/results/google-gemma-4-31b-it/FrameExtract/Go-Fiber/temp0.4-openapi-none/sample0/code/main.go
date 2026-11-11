package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"

	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Post("/extract", func(c *fiber.Ctx) error {
		// Parse multipart form
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid multipart form"})
		}

		// Get frameNumber from form
		frameNumberStr := form.Value("frameNumber")
		frameNumber, err := strconv.Atoi(frameNumberStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid or missing frameNumber"})
		}

		// Get the video file
		file, err := c.FormFile("video")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Video file is missing"})
		}

		// Create a temporary directory for processing
		tempDir, err := os.MkdirTemp("", "frameextract")
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Internal server error"})
		}
		defer os.RemoveAll(tempDir)

		// Save uploaded video to temp file
		videoPath := filepath.Join(tempDir, file.Filename)
		if err := c.SaveFile(file, videoPath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save uploaded video"})
		}

		// Output path for the extracted frame
		outputImage := filepath.Join(tempDir, "frame.png")

		// ffmpeg command:
		// -i <input> : input file
		// -vf "select=eq(n\,<frameNumber>)" : filter to select specific frame index
		// -vframes 1 : output exactly one frame
		// <output> : output file path
		cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n\\,%d)", frameNumber), "-vframes", "1", "-y", outputImage)
		
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber),
			})
		}

		// Check if the output file was actually created (ffmpeg sometimes exits 0 even if no frame was found)
		if _, err := os.Stat(outputImage); os.IsNotExist(err) {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber),
			})
		}

		// Serve the extracted image
		return c.SendFile(outputImage)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}