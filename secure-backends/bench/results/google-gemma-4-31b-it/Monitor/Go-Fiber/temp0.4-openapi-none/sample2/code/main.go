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
	ProcessId     int    `json:"processId"`
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

		// Prepare ps command. 
		// Since "command" parameter is not supported, we use flags passed in filter_flags.
		// Default to "aux" if filter_flags is empty.
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
			return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Failed to execute ps command: %v", err),
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
		
		// Skip header line
		if scanner.Scan() {
			_ = scanner.Text()
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				// ps aux output typically starts with User, PID, %CPU, %MEM...
				// We split by whitespace to extract the PID (usually the second column)
				fields := strings.Fields(line)
				if len(fields) >= 2 {
					pid, err := strconv.Atoi(fields[1])
					if err == nil {
						results = append(results, ProcessInfo{
							ProcessId:     pid,
							ProcessString: line,
						})
					}
				}
			}
		}

		if err := scanner.Err(); err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{
				Code:    500,
				Message: fmt.Sprintf("Error reading ps output: %v", err),
			})
		}

		return c.JSON(results)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}