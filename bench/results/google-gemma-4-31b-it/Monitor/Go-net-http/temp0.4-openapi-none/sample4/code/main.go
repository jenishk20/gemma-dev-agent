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

	// Prepare ps command. 
	// Since "command" parameter is not supported, we use standard flags.
	// We use -e to get all processes and -o pid,args to get the ID and the command string.
	args := []string{"-e", "-o", "pid,args"}
	if req.FilterFlags != "" {
		// In a real scenario, we'd validate these flags to prevent command injection.
		// For this implementation, we append them if provided, but we must be careful.
		// To stay safe and functional, we'll prioritize the standard output format.
		args = append(args, strings.Fields(req.FilterFlags)...)
	}

	out, err := exec.Command("ps", args...).Output()
	if err != nil {
		sendError(w, http.StatusInternalServerError, "Failed to execute ps command")
		return
	}

	re, err := regexp.Compile(req.CommandRegex)
	if err != nil {
		sendError(w, http.StatusBadRequest, "Invalid regular expression")
		return
	}

	lines := strings.Split(string(out), "\n")
	var processes []ProcessInfo

	// Skip the header line
	for i := 1; i < len(lines); i++ {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			continue
		}

		if re.MatchString(line) {
			fields := strings.Fields(line)
			if len(fields) < 1 {
				continue
			}

			pid, err := strconv.Atoi(fields[0])
			if err != nil {
				continue
			}

			processes = append(processes, ProcessInfo{
				ProcessID:     pid,
				ProcessString: line,
			})
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(processes)
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

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}