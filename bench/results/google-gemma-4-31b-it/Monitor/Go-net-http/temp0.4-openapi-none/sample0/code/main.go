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

func monitorHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	var req MonitorRequest
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid request body", 400)
		return
	}

	if req.CommandRegex == "" {
		sendError(w, http.StatusBadRequest, "command_regex is required", 400)
		return
	}

	// Prepare ps command. 
	// We use "ps" with the provided flags. 
	// Since "command" parameter is not supported, we rely on the flags passed in filter_flags.
	// Default to "aux" if no flags provided to ensure we get process IDs and command strings.
	args := []string{}
	if req.FilterFlags != "" {
		args = strings.Fields(req.FilterFlags)
	} else {
		args = []string{"aux"}
	}

	cmd := exec.Command("ps", args...)
	output, err := cmd.Output()
	if err != nil {
		sendError(w, http.StatusInternalServerError, fmt.Sprintf("Failed to execute ps: %v", err), 500)
		return
	}

	re, err := regexp.Compile(req.CommandRegex)
	if err != nil {
		sendError(w, http.StatusBadRequest, "Invalid regular expression", 400)
		return
	}

	lines := strings.Split(string(output), "\n")
	var results []ProcessInfo

	// Skip header line
	for i := 1; i < len(lines); i++ {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			continue
		}

		if re.MatchString(line) {
			fields := strings.Fields(line)
			if len(fields) < 2 {
				continue
			}

			// In 'ps aux', the PID is typically the second column
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

func sendError(w http.ResponseWriter, status int, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(ErrorResponse{
		Code:    code,
		Message: message,
	})
}

func main() {
	http.HandleFunc("/monitor/commands", monitorHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatalf("Server failed: %s", err)
	}
}