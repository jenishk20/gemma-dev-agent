package main

import (
	"bufio"
	"bytes"
	"encoding/json"
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
			// Manual parsing if UnmarshalJSON fails or for specific Fiber versions
			if err := c.BodyParser(&req); err != nil {
				return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
					Code:    400,
					Message: "Invalid request body",
				})
			}
		}

		if req.CommandRegex == "" {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Code:    400,
				Message: "command_regex is required",
			})
		}

		// Compile the regex
		re, err := regexp.Compile(req.CommandRegex)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Code:    400,
				Message: fmt.Sprintf("Invalid regular expression: %v", err),
			})
		}

		// Prepare the ps command
		// If filter_flags is provided, we split it. Otherwise, we use a default.
		args := []string{}
		if req.FilterFlags != "" {
			args = strings.Fields(req.FilterFlags)
		} else {
			// Default to aux to get a wide range of process info
			args = []string{"aux"}
		}

		cmd := exec.Command("ps", args...)
		var out bytes.Buffer
		cmd.Stdout = &out

		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Failed to execute ps command: %v", err),
			})
		}

		var results []ProcessInfo
		scanner := bufio.NewScanner(&out)
		
		// Skip header line
		if scanner.Scan() {
			_ = scanner.Text()
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				fields := strings.Fields(line)
				if len(fields) < 2 {
					continue
				}

				// In 'ps aux', the PID is typically the second column (index 1)
				// However, since flags are dynamic, we try to find the first integer
				// that looks like a PID. For standard 'aux', it's fields[1].
				pidStr := fields[1]
				pid, err := strconv.Atoi(pidStr)
				if err != nil {
					// If the second field isn't a PID, this specific filter_flags 
					// might have changed the output format. We'll skip or try to 
					// guess, but for the sake of this API, we assume standard ps output.
					continue
				}

				results = append(results, ProcessInfo{
					ProcessID:     pid,
					ProcessString: line,
				})
			}
		}

		if err := scanner.Err(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Error reading ps output: %v", err),
			})
		}

		return c.Status(fiber.StatusOK).JSON(results)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}