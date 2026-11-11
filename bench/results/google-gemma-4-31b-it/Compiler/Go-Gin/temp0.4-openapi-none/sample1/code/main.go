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
	FileName    string `json:"fileName"`
	FileContent string `json:"fileContent"`
}

type CompileResponse struct {
	HasError      bool   `json:"hasError"`
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

		if req.FileName == "" || req.FileContent == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "fileName and fileContent are required"})
			return
		}

		// Write content to a temporary file
		tmpDir, err := os.MkdirTemp("", "compilationnow")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not create temp directory"})
			return
		}
		defer os.RemoveAll(tmpDir)

		filePath := filepath.Join(tmpDir, req.FileName)
		if err := os.WriteFile(filePath, []byte(req.FileContent), 0644); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not write file"})
			return
		}

		var cmd *exec.Cmd
		ext := filepath.Ext(req.FileName)

		switch ext {
		case ".ts":
			// tsc returns non-zero on error. We capture stderr and stdout.
			cmd = exec.Command("tsc", filePath)
		case ".cpp":
			// g++ returns non-zero on error.
			cmd = exec.Command("g++", filePath, "-o", filepath+".out")
		default:
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unsupported file extension. Use .ts or .cpp"})
			return
		}

		output, err := cmd.CombinedOutput()
		
		if err != nil {
			errMsg := strings.TrimSpace(string(output))
			if errMsg == "" {
				errMsg = fmt.Sprintf("Compilation failed: %v", err)
			}
			resp := CompileResponse{
				HasError:      true,
				CompilerError: &errMsg,
			}
			c.JSON(http.StatusOK, resp)
		} else {
			resp := CompileResponse{
				HasError:      false,
				CompilerError: nil,
			}
			c.JSON(http.StatusOK, resp)
		}
	})

	r.Run("0.0.0.0:5000")
}