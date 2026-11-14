package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

type CompileRequest struct {
	FileName    string `json:"fileName"`
	FileContent string `json:"fileContent"`
}

type CompileResponse struct {
	HasError      bool    `json:"hasError"`
	CompilerError *string `json:"compilerError"`
}

func handleCompile(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CompileRequest
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		http.Error(w, "Invalid JSON request", http.StatusBadRequest)
		return
	}

	if req.FileName == "" || req.FileContent == "" {
		http.Error(w, "fileName and fileContent are required", http.StatusBadRequest)
		return
	}

	// Create a temporary directory to avoid collisions and security issues
	tmpDir, err := ioutil.TempDir("", "compilationnow")
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tmpDir)

	filePath := filepath.Join(tmpDir, req.FileName)
	if err := ioutil.WriteFile(filePath, []byte(req.FileContent), 0644); err != nil {
		http.Error(w, "Failed to write file", http.StatusInternalServerError)
		return
	}

	var cmd *exec.Cmd
	ext := filepath.Ext(req.FileName)

	switch ext {
	case ".ts":
		// tsc checks for errors. We use --noEmit to just check types.
		cmd = exec.Command("tsc", filePath, "--noEmit", "--esModuleInterop")
	case ".cpp":
		// g++ compiles the file.
		cmd = exec.Command("g++", filePath, "-o", filepath.Join(tmpDir, "out"))
	default:
		http.Error(w, "Unsupported file extension. Use .ts or .cpp", http.StatusBadRequest)
		return
	}

	output, err := cmd.CombinedOutput()
	
	var resp CompileResponse
	if err != nil {
		resp.HasError = true
		errMsg := strings.TrimSpace(string(output))
		if errMsg == "" {
			errMsg = err.Error()
		}
		resp.CompilerError = &errMsg
	} else {
		resp.HasError = false
		resp.CompilerError = nil
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/compile", handleCompile)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}