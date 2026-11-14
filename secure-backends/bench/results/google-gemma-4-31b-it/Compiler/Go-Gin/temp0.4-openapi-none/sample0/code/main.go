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

		if req.FileName == "" || req.FileContent == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "fileName and fileContent are required"})
			return
		}

		// Write file to disk
		err := os.WriteFile(req.FileName, []byte(req.FileContent), 0644)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not write file"})
			return
		}
		defer os.Remove(req.FileName)

		var cmd *exec.Cmd
		ext := filepath.Ext(req.FileName)

		switch ext {
		case ".ts":
			// tsc returns 0 on success, non-zero on error. 
			// We use --noEmit to just check for compilation errors without generating JS.
			cmd = exec.Command("tsc", req.FileName, "--noEmit")
		case ".cpp", ".cc", ".cxx":
			// g++ returns 0 on success. -c means compile only (no linking).
			cmd = exec.Command("g++", "-c", req.FileName)
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
			c.JSON(http.StatusOK, CompileResponse{
				HasError:      true,
				CompilerError: &errMsg,
			})
		} else {
			c.JSON(http.StatusOK, CompileResponse{
				HasError:      false,
				CompilerError: nil,
			})
		}
	})

	r.Run("0.0.0.0:5000")
}