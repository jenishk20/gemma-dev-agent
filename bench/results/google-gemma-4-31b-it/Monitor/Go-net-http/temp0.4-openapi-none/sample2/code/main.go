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

type MonitorRequest struct {
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

func sendError(w http.ResponseWriter, code int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{
		Code:    code,
		Message: message,
	})
}

func monitorHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		sendError(w, http.StatusMethodNotAllowed, "Only POST method is supported")
		return
	}

	var req MonitorRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	if req.CommandRegex == "" {
		sendError(w, http.StatusBadRequest, "command_regex is required")
		return
	}

	// Prepare ps command. 
	// We use "ps" and the provided flags. 
	// Since the prompt mentions "command" parameter is not supported, 
	// we rely on the flags provided in filter_flags (e.g., "aux").
	args := strings.Fields(req.FilterFlags)
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

	var results []ProcessInfo
	lines := strings.Split(string(output), "\n")

	// Skip the header line of ps output
	for i := 1; i < len(lines); i++ {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			continue
		}

		if re.MatchString(line) {
			fields := strings.Fields(line)
			if len(fields) > 0 {
				// In 'ps aux', the PID is usually the 2nd column (index 1)
				// However, since flags are dynamic, we try to find the first integer
				// that looks like a PID. For standard 'aux', it's fields[1].
				pidStr := ""
				if len(fields) > 1 {
					pidStr = fields[1]
				} else {
					pidStr = fields[0]
				}

				pid, err := strconv.Atoi(pidStr)
				if err != nil {
					// If we can't parse the PID, we skip or use 0
					pid = 0
				}

				results = append(results, ProcessInfo{
					ProcessID:     pid,
					ProcessString: line,
				})
			}
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(results)
}

func main() {
	http.HandleFunc("/monitor/commands", monitorHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}