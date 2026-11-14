package main

import (
	"bytes"
	"fmt"
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
		tempDir, err := os.MkdirTemp("", "compilationnow-*")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to create temp directory"})
		}
		defer os.RemoveAll(tempDir)

		filePath := filepath.Join(tempDir, req.FileName)
		if err := os.WriteFile(filePath, []byte(req.FileContent), 0644); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to write source file"})
		}

		var cmd *exec.Cmd
		ext := filepath.Ext(req.FileName)

		switch ext {
		case ".ts":
			// Use tsc (TypeScript Compiler)
			// --noEmit prevents generating .js files, just checks for errors
			cmd = exec.Command("tsc", filePath, "--noEmit", "--esModuleInterop", "false")
		case ".cpp", ".cc", ".cxx":
			// Use g++ for C++ compilation
			// -fsyntax-only checks for compilation errors without producing an executable
			cmd = exec.Command("g++", "-fsyntax-only", filePath)
		default:
			return c.Status(400).JSON(fiber.Map{"error": "Unsupported file extension. Use .ts or .cpp"})
		}

		var stderr bytes.Buffer
		cmd.Stderr = &stderr

		err = cmd.Run()
		if err != nil {
			// Compilation failed
			errMsg := stderr.String()
			if errMsg == "" {
				errMsg = fmt.Sprintf("Compilation failed: %v", err)
			}
			return c.JSON(CompileResponse{
				HasError:      true,
				CompilerError: &errMsg,
			})
		}

		// Compilation succeeded
		return c.JSON(CompileResponse{
			HasError:      false,
			CompilerError: nil,
		})
	})

	app.Listen("0.0.0.0:5000")
}