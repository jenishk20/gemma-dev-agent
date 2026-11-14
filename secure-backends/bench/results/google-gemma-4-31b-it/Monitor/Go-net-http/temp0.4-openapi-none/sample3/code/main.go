package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
)

type RequestBody struct {
	FilterFlags  string `json:"filter_flags"`
	CommandRegex string `json:"command_regex"`
}

type ProcessInfo struct {
	ProcessID     int    `json:"processId"`
	ProcessString string `json:"processString"`
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func main() {
	http.HandleFunc("/monitor/commands", monitorHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}

func monitorHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		sendError(w, http.StatusMethodNotAllowed, "Only POST method is supported")
		return
	}

	var req RequestBody
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid JSON request body")
		return
	}

	if req.CommandRegex == "" {
		sendError(w, http.StatusBadRequest, "command_regex is required")
		return
	}

	// Prepare ps command. 
	// We use 'ps' with the provided flags. If flags are empty, we use 'aux' as a default.
	args := []string{}
	if req.FilterFlags != "" {
		args = strings.Fields(req.FilterFlags)
	} else {
		args = []string{"aux"}
	}

	cmd := exec.Command("ps", args...)
	output, err := cmd.Output()
	if err != nil {
		sendError(w, http.StatusInternalServerError, fmt.Sprintf("Failed to execute ps: %v", err))
		return
	}

	re, err := regexp.Compile(req.CommandRegex)
	if err != nil {
		sendError(w, http.StatusBadRequest, "Invalid regular expression")
		return
	}

	lines := strings.Split(string(output), "\n")
	var results []ProcessInfo

	// ps aux output typically starts with a header. We iterate through lines.
	for _, line := range lines {
		if line == "" {
			continue
		}

		if re.MatchString(line) {
			fields := strings.Fields(line)
			if len(fields) < 2 {
				continue
			}

			// In 'ps aux', the PID is the second column (index 1)
			pid, err := strconv.Atoi(fields[1])
			if err != nil {
				continue
			}

			results = append(results, ProcessInfo{
				ProcessID:     pid,
				ProcessString: line,
			})
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(results)
}

func sendError(w http.ResponseWriter, code int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{
		Code:    code,
		Message: message,
	})
}