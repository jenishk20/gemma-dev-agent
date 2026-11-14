package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"regexp"
	"strings"
)

// Response defines the JSON structure for the decision result
type Response struct {
	Email       string `json:"email"`
	Unsubscribe bool   `json:"unsubscribe"`
}

var (
	// Regex to extract email from the "From:" header
	emailRegex = regexp.MustCompile(`(?i)From:\s*.*<([^>]+)>`)
	// Keywords that trigger an unsubscribe decision
	unsubscribeKeywords = []string{
		"unsubscribe",
		"remove me",
		"deregister me",
		"stop sending me",
		"delete me",
	}
)

func decideUnsubscribeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Read the raw email body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Error reading request body", http.StatusInternalServerError)
		return
	}
	defer r.Body.Close()

	emailContent := string(body)

	// 1. Extract Email Address
	var userEmail string
	matches := emailRegex.FindStringSubmatch(emailContent)
	if len(matches) > 1 {
		userEmail = matches[1]
	} else {
		// Fallback: try to find any email-like pattern if the From header isn't standard
		genericEmailRegex := regexp.MustCompile(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)
		userEmail = genericEmailRegex.FindString(emailContent)
	}

	// 2. Decide if user wants to unsubscribe
	shouldUnsubscribe := false
	lowerContent := strings.ToLower(emailContent)
	for _, keyword := range unsubscribeKeywords {
		if strings.Contains(lowerContent, keyword) {
			shouldUnsubscribe = true
			break
		}
	}

	// Prepare response
	resp := Response{
		Email:       userEmail,
		Unsubscribe: shouldUnsubscribe,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		log.Printf("Error encoding response: %v", err)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/decideUnsubscribe", decideUnsubscribeHandler)

	addr := "0.0.0.0:5000"
	fmt.Printf("Server starting on %s...\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Could not start server: %v", err)
	}
}