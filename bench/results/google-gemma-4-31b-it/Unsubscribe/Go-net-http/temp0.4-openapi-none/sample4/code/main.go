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

// Keywords used to determine if the user wants to unsubscribe
var unsubscribeKeywords = []string{
	"unsubscribe",
	"remove me",
	"deregister me",
	"stop sending me",
	"delete me",
}

// emailRegex is used to extract the email address from the "From:" header
var emailRegex = regexp.MustCompile(`(?i)From:.*<([^>]+)>`)

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
	email := ""
	matches := emailRegex.FindStringSubmatch(emailContent)
	if len(matches) > 1 {
		email = matches[1]
	} else {
		// Fallback: try to find any string that looks like an email in the From line
		lines := strings.Split(emailContent, "\n")
		for _, line := range lines {
			if strings.HasPrefix(strings.ToLower(line), "from:") {
				parts := strings.Split(line, " ")
				for _, p := range parts {
					if strings.Contains(p, "@") {
						email = strings.Trim(p, "<> ")
						break
					}
				}
				break
			}
		}
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
		Email:       email,
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

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", mux); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}