package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
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

func compileHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CompileRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.FileName == "" || req.FileContent == "" {
		http.Error(w, "fileName and fileContent are required", http.StatusBadRequest)
		return
	}

	// Create a temporary directory for the compilation process to avoid collisions
	tmpDir, err := ioutil.TempDir("", "compilationnow")
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer os.RemoveAll(tmpDir)

	filePath := filepath.Join(tmpDir, req.FileName)
	if err := ioutil.WriteFile(filePath, []byte(req.FileContent), 0644); err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	var cmd *exec.Cmd
	ext := filepath.Ext(req.FileName)

	switch ext {
	case ".ts":
		// tsc compiles TS to JS. We use --noEmit to just check for errors.
		cmd = exec.Command("tsc", filePath, "--noEmit", "--esModuleInterop")
	case ".cpp":
		// g++ compiles C++. We use -fsyntax-only to check for compilation errors without producing a binary.
		cmd = exec.Command("g++", "-fsyntax-only", filePath)
	default:
		http.Error(w, "Unsupported file extension. Please use .ts or .cpp", http.StatusBadRequest)
		return
	}

	output, err := cmd.CombinedOutput()
	
	var resp CompileResponse
	if err != nil {
		resp.HasError = true
		errMsg := strings.TrimSpace(string(output))
		if errMsg == "" {
			errMsg = fmt.Sprintf("Compilation failed: %v", err)
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
	http.HandleFunc("/compile", compileHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		fmt.Printf("Error starting server: %s\n", err)
		os.Exit(1)
	}
}