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

		// Prepare ps command. 
		// We split filter_flags by space to pass as separate arguments to exec.Command
		args := []string{}
		if req.FilterFlags != "" {
			args = append(args, strings.Fields(req.FilterFlags)...)
		}

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
		scanner := bufio.NewScanner(&out)
		
		// Skip the header line of ps output
		if scanner.Scan() {
			_ = scanner.Text()
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				// ps output usually starts with PID. 
				// We attempt to extract the first integer found in the line as the PID.
				fields := strings.Fields(line)
				if len(fields) > 0 {
					pid, err := strconv.Atoi(fields[0])
					if err == nil {
						results = append(results, ProcessInfo{
							ProcessID:     pid,
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