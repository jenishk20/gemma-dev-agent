package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
)

type CompileRequest struct {
	FileName    string `json:"fileName" binding:"required"`
	FileContent string `json:"fileContent" binding:"required"`
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

		// Create a temporary directory for the compilation process
		tempDir, err := os.MkdirTemp("", "compilationnow-*")
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
		ext := filepath.Ext(req.FileName)

		switch ext {
		case ".ts":
			// Use tsc for TypeScript compilation
			// --noEmit prevents generating js files, we only care about the check
			cmd = exec.Command("tsc", filePath, "--noEmit", "--esModuleInterop", "false")
		case ".cpp":
			// Use g++ for C++ compilation
			cmd = exec.Command("g++", filePath, "-o", filepath+ ".out")
		default:
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unsupported file extension. Use .ts or .cpp"})
			return
		}

		output, err := cmd.CombinedOutput()
		
		if err != nil {
			// Compilation failed
			errMsg := strings.TrimSpace(string(output))
			if errMsg == "" {
				errMsg = err.Error()
			}
			c.JSON(http.StatusOK, CompileResponse{
				HasError:      true,
				CompilerError: &errMsg,
			})
		} else {
			// Compilation succeeded
			c.JSON(http.StatusOK, CompileResponse{
				HasError:      false,
				CompilerError: nil,
			})
		}
	})

	r.Run("0.0.0.0:5000")
}