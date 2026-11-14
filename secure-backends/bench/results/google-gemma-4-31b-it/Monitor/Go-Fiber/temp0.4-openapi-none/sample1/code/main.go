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
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Code:    400,
				Message: "Invalid request body",
			})
		}

		if req.CommandRegex == "" {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
				Code:    400,
				Message: "command_regex is required",
			})
		}

		// Prepare ps command. Split flags by space.
		args := []string{}
		if req.FilterFlags != "" {
			args = strings.Fields(req.FilterFlags)
		}

		// Execute ps command
		cmd := exec.Command("ps", args...)
		var out bytes.Buffer
		cmd.Stdout = &out
		if err := cmd.Run(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Failed to execute ps: %v", err),
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

		var results []ProcessInfo
		scanner := bufio.NewScanner(&out)
		
		// Skip header if it exists (common in ps aux)
		firstLine := true
		for scanner.Scan() {
			line := scanner.Text()
			if firstLine {
				firstLine = false
				// Basic check to see if first line is a header (contains PID or USER)
				if strings.Contains(line, "PID") || strings.Contains(line, "USER") {
					continue
				}
			}

			if re.MatchString(line) {
				pid := extractPID(line)
				if pid != -1 {
					results = append(results, ProcessInfo{
						ProcessID:     pid,
						ProcessString: line,
					})
				}
			}
		}

		return c.JSON(results)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

// extractPID attempts to find the process ID in a ps output line.
// Since ps output formats vary, we look for the first integer that looks like a PID.
func extractPID(line string) int {
	fields := strings.Fields(line)
	if len(fields) == 0 {
		return -1
	}

	// In 'ps aux', PID is usually the 2nd column.
	// We try to find the first field that is a valid integer and not the first field 
	// (which is usually the USER) unless it's the only field.
	for i, field := range fields {
		// Skip the first field if it's likely a username (non-numeric)
		if i == 0 && !isNumeric(field) {
			continue
		}
		if pid, err := strconv.Atoi(field); err == nil {
			return pid
		}
	}
	return -1
}

func isNumeric(s string) bool {
	_, err := strconv.Atoi(s)
	return err == nil
}