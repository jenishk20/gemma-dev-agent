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
	ProcessId     int    `json:"processId"`
	ProcessString string `json:"processString"`
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func monitorHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	var req RequestBody
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	if req.CommandRegex == "" {
		sendError(w, http.StatusBadRequest, "command_regex is required")
		return
	}

	// Construct ps command. 
	// We use 'ps' and the provided flags. If flags are empty, we use basic 'aux'
	flags := req.FilterFlags
	if flags == "" {
		flags = "aux"
	}

	// Execute ps command
	// Split flags by space to pass as separate arguments to exec.Command
	args := strings.Fields(flags)
	cmd := exec.Command("ps", args...)
	output, err := cmd.Output()
	if err != nil {
		sendError(w, http.StatusInternalServerError, fmt.Sprintf("Failed to execute ps: %v", err))
		return
	}

	// Compile the regex
	re, err := regexp.Compile(req.CommandRegex)
	if err != nil {
		sendError(w, http.StatusBadRequest, "Invalid regular expression")
		return
	}

	var results []ProcessInfo
	lines := strings.Split(string(output), "\n")

	// Skip the header line (usually the first line of ps output)
	for i := 1; i < len(lines); i++ {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			continue
		}

		if re.MatchString(line) {
			// Extract PID. In 'ps aux' or similar, PID is usually the second column.
			// However, since flags are dynamic, we rely on the fact that ps output 
			// starts with columns. We'll try to find the first integer in the line.
			fields := strings.Fields(line)
			if len(fields) > 0 {
				pid, err := strconv.Atoi(fields[0]) 
				// Note: In 'ps aux', PID is index 1. In 'ps', it's index 0.
				// Since we don't know the exact flags, we attempt to find the first numeric field.
				if err != nil {
					// Try second field if first isn't a number (common in aux)
					if len(fields) > 1 {
						pid, err = strconv.Atoi(fields[1])
					}
				}

				if err == nil {
					results = append(results, ProcessInfo{
						ProcessId:     pid,
						ProcessString: line,
					})
				}
			}
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

func main() {
	http.HandleFunc("/monitor/commands", monitorHandler)

	log.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}