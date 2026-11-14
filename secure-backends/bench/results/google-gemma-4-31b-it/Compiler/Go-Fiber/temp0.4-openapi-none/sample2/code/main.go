package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

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
		tmpDir, err := os.MkdirTemp("", "compilationnow-*")
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
			// tsc checks for errors. We use --noEmit to just check types/syntax
			cmd = exec.Command("tsc", filePath, "--noEmit", "--esModuleInterop", "--target", "es5")
		case ".cpp", ".cc", ".cxx":
			// g++ compilation check
			cmd = exec.Command("g++", filePath, "-o", filepath+ ".out")
		default:
			return c.Status(400).JSON(fiber.Map{"error": "Unsupported file extension. Use .ts or .cpp"})
		}

		output, err := cmd.CombinedOutput()
		
		if err != nil {
			errMsg := strings.TrimSpace(string(output))
			if errMsg == "" {
				errMsg = fmt.Sprintf("Compilation failed: %v", err)
			}
			
			res := CompileResponse{
				HasError:      true,
				CompilerError: &errMsg,
			}
			return c.JSON(res)
		}

		return c.JSON(CompileResponse{
			HasError:      false,
			CompilerError: nil,
		})
	})

	app.Listen("0.0.0.0:5000")
}