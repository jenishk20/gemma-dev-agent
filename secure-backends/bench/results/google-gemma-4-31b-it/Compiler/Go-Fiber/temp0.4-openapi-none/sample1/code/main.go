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

		// Create a temporary file to store the code
		tmpFile, err := os.CreateTemp("", req.FileName)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Could not create temporary file"})
		}
		defer os.Remove(tmpFile.Name())

		if _, err := tmpFile.WriteString(req.FileContent); err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Could not write to temporary file"})
		}
		tmpFile.Close()

		ext := filepath.Ext(req.FileName)
		var cmd *exec.Cmd

		switch ext {
		case ".ts":
			// tsc returns non-zero exit code on compilation errors
			// We use --noEmit to just check for errors without generating JS files
			cmd = exec.Command("tsc", tmpFile.Name(), "--noEmit", "--esModuleInterop")
		case ".cpp", ".cc", ".cxx":
			// g++ returns non-zero exit code on compilation errors
			// -save-temps is not needed, we just want to see if it compiles
			cmd = exec.Command("g++", tmpFile.Name(), "-o", "/dev/null")
		default:
			return c.Status(400).JSON(fiber.Map{"error": "Unsupported file extension. Please use .ts or .cpp"})
		}

		output, err := cmd.CombinedOutput()
		
		if err != nil {
			errMsg := strings.TrimSpace(string(output))
			if errMsg == "" {
				errMsg = fmt.Sprintf("Compilation failed: %v", err)
			}
			return c.JSON(CompileResponse{
				HasError:      true,
				CompilerError: &errMsg,
			})
		}

		return c.JSON(CompileResponse{
			HasError:      false,
			CompilerError: nil,
		})
	})

	app.Listen("0.0.0.0:5000")
}