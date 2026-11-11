package main

import (
	"bufio"
	"bytes"
	"fmt"
	"log"
	"os/exec"
	"regexp"
	"strconv"
	"strings"

	"github.com/gofiber/fiber/v2"
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

func main() {
	app := fiber.New()

	app.Post("/monitor/commands", func(c *fiber.Ctx) error {
		var req MonitorRequest
		if err := c.RequestBody().UnmarshalJSON(&req); err != nil {
			// Using BodyParser for Fiber v2
		}
		// Re-parsing using BodyParser for reliability in Fiber v2
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(ErrorResponse{
				Code:    400,
				Message: "Invalid request body",
			})
		}

		if req.CommandRegex == "" {
			return c.Status(400).JSON(ErrorResponse{
				Code:    400,
				Message: "command_regex is required",
			})
		}

		// Prepare the ps command
		// Since "command" parameter is not supported, we use the flags provided in filter_flags
		// Default to "aux" if filter_flags is empty
		args := []string{}
		if req.FilterFlags != "" {
			args = strings.Fields(req.FilterFlags)
		} else {
			args = []string{"aux"}
		}

		cmd := exec.Command("ps", args...)
		var out bytes.Buffer
		cmd.Stdout = &out

		if err := cmd.Run(); err != nil {
			return c.Status(500).JSON(ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Failed to execute ps command: %v", err),
			})
		}

		// Compile regex
		re, err := regexp.Compile(req.CommandRegex)
		if err != nil {
			return c.Status(400).JSON(ErrorResponse{
				Code:    400,
				Message: fmt.Sprintf("Invalid regular expression: %v", err),
			})
		}

		var results []ProcessInfo
		scanner := bufio.NewScanner(&out)
		
		// Skip header line
		if scanner.Scan() {
			// Header skipped
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				fields := strings.Fields(line)
				if len(fields) < 2 {
					continue
				}

				// In 'ps aux', the PID is usually the second column (index 1)
				// However, since filter_flags can change the output format, 
				// we attempt to find the first integer in the line that looks like a PID.
				// For standard 'aux', it's fields[1].
				pid, err := strconv.Atoi(fields[1])
				if err != nil {
					// Fallback: try to find any numeric field that could be a PID
					found := false
					for _, f := range fields {
						if p, e := strconv.Atoi(f); e == nil {
							pid = p
							found = true
							break
						}
					}
					if !found {
						continue
					}
				}

				results = append(results, ProcessInfo{
					ProcessID:     pid,
					ProcessString: line,
				})
			}
		}

		return c.JSON(results)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}