package main

import (
	"bytes"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
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
	r := gin.Default()

	r.POST("/compile", func(c *gin.Context) {
		var req CompileRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Create a unique temporary directory for this request to avoid collisions
		tempDir, err := os.MkdirTemp("", "compile-now-")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create temp dir"})
			return
		}
		defer os.RemoveAll(tempDir)

		filePath := filepath.Join(tempDir, req.FileName)
		if err := os.WriteFile(filePath, []byte(req.FileContent), 0644); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to write file"})
			return
		}

		var cmd *exec.Cmd
		ext := strings.ToLower(filepath.Ext(req.FileName))

		switch ext {
		case ".ts":
			// tsc (TypeScript Compiler)
			// --noEmit prevents generating js files, we only care about errors
			cmd = exec.Command("tsc", filePath, "--noEmit", "--esModuleInterop", "false")
		case ".cpp":
			// g++ (C++ Compiler)
			// -fsyntax-only checks for compilation errors without producing an executable
			cmd = exec.Command("g++", "-fsyntax-only", filePath)
		default:
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unsupported file extension. Use .ts or .cpp"})
			return
		}

		var stderr bytes.Buffer
		cmd.Stderr = &stderr

		err = cmd.Run()

		if err != nil {
			// Compilation failed
			errMsg := stderr.String()
			if errMsg == "" {
				errMsg = "Unknown compilation error"
			}
			resp := CompileResponse{
				HasError:      true,
				CompilerError: &errMsg,
			}
			c.JSON(http.StatusOK, resp)
		} else {
			// Compilation succeeded
			resp := CompileResponse{
				HasError:      false,
				CompilerError: nil,
			}
			c.JSON(http.StatusOK, resp)
		}
	})

	r.Run("0.0.0.0:5000")
}

func init() {
	// Ensure we have a unique ID for the process if needed, though not explicitly required by schema
	_ = uuid.New().String()
}