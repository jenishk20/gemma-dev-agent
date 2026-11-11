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
			return c.Status(400).JSON(fiber.Map{"error": "Invalid multipart form"})
		}

		// Get frameNumber
		frameNumStr := form.Value("frameNumber")
		frameNum, err := strconv.Atoi(frameNumStr)
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "frameNumber must be an integer"})
		}

		// Get video file
		videoFile, err := form.File("video")
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "video file is required"})
		}

		// Create temporary directory for processing
		tempDir, err := os.MkdirTemp("", "frameextract")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Internal server error"})
		}
		defer os.RemoveAll(tempDir)

		// Save uploaded video to temp path
		videoPath := filepath.Join(tempDir, "input_video")
		if err := c.SaveFile(videoFile, videoPath); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to save uploaded video"})
		}

		// Output path for the extracted frame
		outputPath := filepath.Join(tempDir, "frame.png")

		// FFmpeg command to extract a specific frame
		// -i: input file
		// -vf "select=eq(n\,X)": filter to select frame index X
		// -vframes 1: output only one frame
		cmd := exec.Command("ffmpeg", "-i", videoPath, "-vf", fmt.Sprintf("select=eq(n,%d)", frameNum), "-vframes", "1", "-f", "image2", "-y", outputPath)
		
		if err := cmd.Run(); err != nil {
			return c.Status(404).JSON(fiber.Map{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNum)})
		}

		// Check if file was actually created (ffmpeg sometimes exits 0 even if frame is out of range)
		if _, err := os.Stat(outputPath); os.IsNotExist(err) {
			return c.Status(404).JSON(fiber.Map{"error": fmt.Sprintf("Frame at index %d could not be found.", frameNum)})
		}

		// Return the image file
		return c.SendFile(outputPath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}