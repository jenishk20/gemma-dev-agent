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

		// Compile the regex for filtering
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

		// Skip header line if present (standard ps output usually has one)
		if scanner.Scan() {
			// We don't process the first line as it's usually the header
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				// Attempt to extract PID. 
				// Standard ps output usually starts with PID or has it in a predictable column.
				// We split by whitespace and try to find the first integer.
				fields := strings.Fields(line)
				if len(fields) == 0 {
					continue
				}

				pid, err := strconv.Atoi(fields[0])
				if err != nil {
					// If the first field isn't the PID (e.g. aux format), 
					// we search for the first field that is an integer.
					foundPid := false
					for _, field := range fields {
						if p, e := strconv.Atoi(field); e == nil {
							pid = p
							foundPid = true
							break
						}
					}
					if !foundPid {
						continue
					}
				}

				results = append(results, ProcessInfo{
					ProcessId:     pid,
					ProcessString: line,
				})
			}
		}

		c.JSON(http.StatusOK, results)
	})

	r.Run("0.0.0.0:5000")
}