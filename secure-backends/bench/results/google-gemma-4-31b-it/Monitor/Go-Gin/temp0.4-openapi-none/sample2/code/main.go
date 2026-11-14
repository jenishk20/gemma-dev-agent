package main

import (
	"bufio"
	"bytes"
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
	ProcessID     int    `json:"processId"`
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
		// We use the provided filter_flags if present, otherwise default to "aux"
		flags := req.FilterFlags
		if flags == "" {
			flags = "aux"
		}

		// Split flags into arguments for exec.Command
		args := strings.Fields(flags)
		cmd := exec.Command("ps", args...)

		var out bytes.Buffer
		cmd.Stdout = &out
		if err := cmd.Run(); err != nil {
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
		scanner := bufio.NewScanner(&out)
		
		// Skip the header line of ps output
		if scanner.Scan() {
			_ = scanner.Text()
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				// Extract PID. In 'ps aux' or similar, PID is typically the second column.
				// We split by whitespace and try to find the first integer that looks like a PID.
				fields := strings.Fields(line)
				if len(fields) < 2 {
					continue
				}

				// In standard 'ps aux', the second field is the PID.
				pid, err := strconv.Atoi(fields[1])
				if err != nil {
					// If the second field isn't a PID, this specific ps output format 
					// might differ, but for 'aux' it is standard.
					continue
				}

				results = append(results, ProcessInfo{
					ProcessID:     pid,
					ProcessString: line,
				})
			}
		}

		c.JSON(http.StatusOK, results)
	})

	r.Run("0.0.0.0:5000")
}