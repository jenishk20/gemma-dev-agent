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
		// Since "command" parameter is not supported, we use flags provided in filter_flags.
		// We split filter_flags into a slice for exec.Command.
		args := strings.Fields(req.FilterFlags)
		cmd := exec.Command("ps", args...)

		output, err := cmd.Output()
		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Failed to execute ps command: %v", err),
			})
			return
		}

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
		
		// Skip the header line of ps output
		if scanner.Scan() {
			_ = scanner.Text()
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				fields := strings.Fields(line)
				if len(fields) == 0 {
					continue
				}

				// In standard 'ps aux' or similar, the PID is usually the 2nd column (index 1)
				// However, since filter_flags is dynamic, we try to find the first integer 
				// that looks like a PID in the line to be more robust, or assume standard index.
				// For this implementation, we attempt to parse the first field that is a number.
				var pid int
				foundPid := false
				for _, field := range fields {
					if val, err := strconv.Atoi(field); err == nil {
						pid = val
						foundPid = true
						break
					}
				}

				if foundPid {
					results = append(results, ProcessInfo{
						ProcessId:     pid,
						ProcessString: line,
					})
				}
			}
		}

		c.JSON(http.StatusOK, results)
	})

	r.Run("0.0.0.0:5000")
}