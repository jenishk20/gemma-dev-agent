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

	app.Post("/extract", func(c *fiber.Ctx) error {
		// Parse multipart form
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid multipart form"})
		}

		// Get frameNumber
		frameNumberStr := form.Value["frameNumber"]
		if len(frameNumberStr) == 0 {
			return c.Status(400).JSON(fiber.Map{"error": "frameNumber is required"})
		}
		frameNumber, err := strconv.Atoi(frameNumberStr[0])
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "frameNumber must be an integer"})
		}

		// Get video file
		videoFile, err := c.FormFile("video")
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "video file is required"})
		}

		// Create unique IDs for temporary files to avoid collisions
		requestID := uuid.New().String()
		tempInputPath := filepath.Join(os.TempDir(), requestID+"_input"+filepath.Ext(videoFile.Filename))
		tempOutputPath := filepath.Join(os.TempDir(), requestID+"_out.png")

		// Save uploaded video to disk
		if err := c.SaveFile(videoFile, tempInputPath); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to save uploaded video"})
		}

		// Ensure cleanup of temp files
		defer os.Remove(tempInputPath)
		defer os.Remove(tempOutputPath)

		// FFmpeg command to extract a specific frame
		// -i: input file
		// -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
		// -vframes 1: output exactly one frame
		// -f image2: force image format
		cmd := exec.Command("ffmpeg", 
			"-i", tempInputPath, 
			"-vf", fmt.Sprintf("select=eq(n\,%d)", frameNumber), 
			"-vframes", "1", 
			"-f", "image2", 
			tempOutputPath,
		)

		if err := cmd.Run(); err != nil {
			return c.Status(404).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber),
			})
		}

		// Check if the output file was actually created (ffmpeg sometimes exits 0 without writing if frame is out of bounds)
		if _, err := os.Stat(tempOutputPath); os.IsNotExist(err) {
			return c.Status(404).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber),
			})
		}

		// Return the image file
		return c.SendFile(tempOutputPath)
	})

	app.Listen(":5000")
}