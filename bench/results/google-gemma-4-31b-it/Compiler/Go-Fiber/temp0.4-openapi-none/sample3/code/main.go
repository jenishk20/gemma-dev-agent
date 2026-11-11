package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

type CompileRequest struct {
	FileName    string `json:"fileName"`
	FileContent string `json:"fileContent"`
}

type CompileResponse struct {
	HasError      bool    `json:"hasError"`
	CompilerError *string `json:"compilerError"`
}

func main() {
	app := fiber.New()

	app.Post("/compile", func(c *fiber.Ctx) error {
		var req CompileRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
		}

		if req.FileName == "" || req.FileContent == "" {
			return c.Status(400).JSON(fiber.Map{"error": "fileName and fileContent are required"})
		}

		// Create a unique temporary directory for this compilation attempt
		tmpDir, err := os.MkdirTemp("", "compile-*")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to create temp directory"})
		}
		defer os.RemoveAll(tmpDir)

		filePath := filepath.Join(tmpDir, req.FileName)
		if err := os.WriteFile(filePath, []byte(req.FileContent), 0644); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to write source file"})
		}

		var cmd *exec.Cmd
		ext := filepath.Ext(req.FileName)

		switch ext {
		case ".ts":
			// Use tsc to check for errors. --noEmit prevents generating .js files.
			cmd = exec.Command("tsc", filePath, "--noEmit", "--esModuleInterop", "--target", "es6")
		case ".cpp", ".cc", ".cxx":
			// Use g++ to compile. -fsyntax-only checks for errors without producing a binary.
			cmd = exec.Command("g++", "-fsyntax-only", filePath)
		default:
			return c.Status(400).JSON(fiber.Map{"error": "Unsupported file extension. Please use .ts or .cpp"})
		}

		// Capture combined output (stdout and stderr)
		output, err := cmd.CombinedOutput()

		if err != nil {
			errStr := string(output)
			if errStr == "" {
				errStr = fmt.Sprintf("Compilation failed: %v", err)
			}
			return c.JSON(CompileResponse{
				HasError:      true,
				CompilerError: &errStr,
			})
		}

		return c.JSON(CompileResponse{
			HasError:      false,
			CompilerError: nil,
		})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}