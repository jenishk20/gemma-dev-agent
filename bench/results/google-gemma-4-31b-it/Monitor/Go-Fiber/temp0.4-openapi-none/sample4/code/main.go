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

		// Prepare ps command arguments
		// The schema suggests filter_flags match 'ps' flags (e.g., "aux -T")
		args := []string{}
		if req.FilterFlags != "" {
			args = append(args, strings.Fields(req.FilterFlags)...)
		} else {
			// Default to basic listing if no flags provided
			args = append(args, "-e", "-o", "pid,args")
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
			// Header ignored
		}

		for scanner.Scan() {
			line := scanner.Text()
			if re.MatchString(line) {
				fields := strings.Fields(line)
				if len(fields) == 0 {
					continue
				}

				// Attempt to parse PID from the first field
				pid, err := strconv.Atoi(fields[0])
				if err != nil {
					// If the first field isn't a PID, the flags provided might 
					// not be outputting PID first. We skip or handle as raw.
					continue
				}

				results = append(results, ProcessInfo{
					ProcessId:     pid,
					ProcessString: line,
				})
			}
		}

		return c.JSON(results)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}