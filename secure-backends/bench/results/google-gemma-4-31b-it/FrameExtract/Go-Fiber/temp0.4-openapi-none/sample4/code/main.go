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

	app.Post("/extract", func(c *fiber.Ctx) error {
		// Parse multipart form
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid multipart form"})
		}

		// Get frameNumber from form
		frameNumStr := form.Value("frameNumber")
		if frameNumStr == "" {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "frameNumber is required"})
		}
		frameNum, err := strconv.Atoi(frameNumStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "frameNumber must be an integer"})
		}

		// Get video file
		videoFile, err := form.File("video")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "video file is required"})
		}

		// Create unique filenames to avoid collisions
		requestID := uuid.New().String()
		tempInputPath := filepath.Join(os.TempDir(), requestID+"_input"+filepath.Ext(videoFile.Filename))
		tempOutputPath := filepath.Join(os.TempDir(), requestID+"_output.png")

		// Save uploaded file to disk for ffmpeg to process
		if err := c.SaveFile(videoFile, tempInputPath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save uploaded video"})
		}

		// Cleanup files after request
		defer os.Remove(tempInputPath)
		defer os.Remove(tempOutputPath)

		// FFmpeg command to extract a specific frame
		// -i: input file
		// -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
		// -vframes 1: output only one frame
		// -f image2: force image format
		cmd := exec.Command("ffmpeg",
			"-i", tempInputPath,
			"-vf", fmt.Sprintf("select=eq(n,%d)", frameNum),
			"-vframes", "1",
			"-f", "image2",
			tempOutputPath,
		)

		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNum),
			})
		}

		// Check if output file was actually created
		if _, err := os.Stat(tempOutputPath); os.IsNotExist(err) {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNum),
			})
		}

		// Return the image file
		return c.SendFile(tempOutputPath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}