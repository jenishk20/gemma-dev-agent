package main

import (
	"bufio"
	"fmt"
	"net/http"
	"os/exec"
	"regexp"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

type MonitorRequest struct {
	FilterFlags  string `json:"filter_flags"`
	CommandRegex string `json:"command_regex" binding:"required"`
}

type ProcessInfo struct {
	ProcessId     int    `json:"processId"`
	ProcessString string `json:"processString"`
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func main() {
	r := gin.Default()

	r.POST("/monitor/commands", func(c *gin.Context) {
		var req MonitorRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{
				Code:    400,
				Message: "Invalid request body: command_regex is required",
			})
			return
		}

		// Prepare the ps command. 
		// We split filter_flags by space to pass them as separate arguments.
		args := []string{}
		if req.FilterFlags != "" {
			args = strings.Fields(req.FilterFlags)
		}

		cmd := exec.Command("ps", args...)
		output, err := cmd.Output()
		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Failed to execute ps command: %v", err),
			})
			return
		}

		// Compile the regex
		re, err := regexp.Compile(req.CommandRegex)
		if err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{
				Code:    400,
				Message: fmt.Sprintf("Invalid regular expression: %v", err),
			})
			return
		}

		var results []ProcessInfo
		scanner := bufio.NewScanner(strings.NewReader(string(output)))
		
		// Skip header line if present (common for ps aux)
		firstLine := true
		for scanner.Scan() {
			line := scanner.Text()
			if firstLine {
				firstLine = false
				// We check if the first line is actually a header (usually contains "PID")
				if !strings.Contains(line, "PID") {
					// If it doesn't look like a header, process it anyway
				} else {
					continue
				}
			}

			if re.MatchString(line) {
				fields := strings.Fields(line)
				if len(fields) > 0 {
					// Attempt to find the PID. 
					// In standard 'ps aux', PID is the second column.
					// However, since flags are dynamic, we try to find the first integer.
					pid := -1
					for _, field := range fields {
						if val, err := strconv.Atoi(field); err == nil {
							pid = val
							break
						}
					}

					if pid != -1 {
						results = append(results, ProcessInfo{
							ProcessId:     pid,
							ProcessString: line,
						})
					}
				}
			}
		}

		c.JSON(http.StatusOK, results)
	})

	r.Run("0.0.0.0:5000")
}