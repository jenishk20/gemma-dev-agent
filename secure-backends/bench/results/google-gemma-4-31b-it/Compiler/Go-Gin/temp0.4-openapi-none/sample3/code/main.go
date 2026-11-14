package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"

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
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
			return
		}

		// Use a unique directory for each request to avoid collisions
		tempDir, err := os.MkdirTemp("", "compilationnow-*")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not create temp directory"})
			return
		}
		defer os.RemoveAll(tempDir)

		filePath := filepath.Join(tempDir, req.FileName)
		if err := os.WriteFile(filePath, []byte(req.FileContent), 0644); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not write file"})
			return
		}

		var cmd *exec.Cmd
		ext := filepath.Ext(req.FileName)

		switch ext {
		case ".ts":
			// tsc compiles TypeScript. We use --noEmit to just check for errors.
			cmd = exec.Command("tsc", filePath, "--noEmit", "--noEmitTemplated")
		case ".cpp":
			// g++ compiles C++. We use -fsyntax-only to check for errors without producing a binary.
			cmd = exec.Command("g++", "-fsyntax-only", filePath)
		default:
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unsupported file extension. Please use .ts or .cpp"})
			return
		}

		output, err := cmd.CombinedOutput()
		if err != nil {
			// Compilation failed
			errMsg := string(output)
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