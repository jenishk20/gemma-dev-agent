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
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "frameNumber must be an integer"})
		}

		// Get video file
		videoFile, err := form.File("video")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "video file is required"})
		}

		// Create temporary directory for processing
		tempDir, err := os.MkdirTemp("", "frameextract")
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Internal server error"})
		}
		defer os.RemoveAll(tempDir)

		// Save uploaded video to temp file
		inputPath := filepath.Join(tempDir, "input_video")
		if err := c.SaveFile(videoFile, inputPath); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save upload"})
		}

		// Output path for the extracted frame
		outputPath := filepath.Join(tempDir, "frame.png")

		// FFmpeg command to extract a specific frame
		// -i: input file
		// -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
		// -vframes 1: output exactly one frame
		cmd := exec.Command("ffmpeg", "-i", inputPath, "-vf", fmt.Sprintf("select=eq(n\\,%d)", frameNumber), "-vframes", "1", "-q:v", "2", outputPath)
		
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber),
			})
		}

		// Check if the output file was actually created
		if _, err := os.Stat(outputPath); os.IsNotExist(err) {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": fmt.Sprintf("Frame at index %d could not be found.", frameNumber),
			})
		}

		// Send the image file as response
		return c.SendFile(outputPath)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}