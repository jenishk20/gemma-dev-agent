package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/gofiber/fiber/v2"
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

		// Create a temporary file to hold the code
		tmpFile, err := os.CreateTemp("", "compilationnow_*"+filepath.Ext(req.FileName))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to create temp file"})
		}
		defer os.Remove(tmpFile.Name())

		if _, err := tmpFile.WriteString(req.FileContent); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to write content"})
		}
		tmpFile.Close()

		var cmd *exec.Cmd
		ext := filepath.Ext(req.FileName)

		switch ext {
		case ".ts":
			// tsc returns 0 on success, non-zero on error. 
			// We use --noEmit to just check for compilation errors.
			cmd = exec.Command("tsc", tmpFile.Name(), "--noEmit")
		case ".cpp", ".cc", ".cxx":
			// g++ returns 0 on success. -fsyntax-only checks for compilation errors without producing a binary.
			cmd = exec.Command("g++", "-fsyntax-only", tmpFile.Name())
		default:
			return c.Status(400).JSON(fiber.Map{"error": "Unsupported file extension. Please use .ts or .cpp"})
		}

		output, err := cmd.CombinedOutput()
		if err != nil {
			// Compilation failed
			errMsg := string(output)
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