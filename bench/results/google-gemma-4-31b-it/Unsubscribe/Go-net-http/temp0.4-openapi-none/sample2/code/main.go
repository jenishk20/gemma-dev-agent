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

// Response represents the JSON response for the decideUnsubscribe endpoint
type Response struct {
	Email       string `json:"email"`
	Unsubscribe bool   `json:"unsubscribe"`
}

// keywords to look for in the email body
var unsubscribeKeywords = []string{
	"unsubscribe",
	"remove me",
	"deregister me",
	"stop sending me",
	"delete me",
}

// emailRegex is used to extract the email address from the "From:" header
var emailRegex = regexp.MustCompile(`(?i)From:\s*[^<]*<([^>]+)>|From:\s*([^\s\r\n]+)`)

func decideUnsubscribeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Read the raw email body
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Error reading request body", http.StatusInternalServerError)
		return
	}
	defer r.Body.Close()

	body := string(bodyBytes)
	lowerBody := strings.ToLower(body)

	// 1. Determine if the user wants to unsubscribe
	shouldUnsubscribe := false
	for _, keyword := range unsubscribeKeywords {
		if strings.Contains(lowerBody, keyword) {
			shouldUnsubscribe = true
			break
		}
	}

	// 2. Extract the email address from the "From:" header
	email := ""
	matches := emailRegex.FindStringSubmatch(body)
	if len(matches) > 0 {
		// The regex has two capturing groups: one for <email> and one for plain email
		for i := 1; i < len(matches); i++ {
			if matches[i] != "" {
				email = matches[i]
				break
			}
		}
	}

	// Construct response
	resp := Response{
		Email:       email,
		Unsubscribe: shouldUnsubscribe,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		log.Printf("Error encoding JSON: %v", err)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/decideUnsubscribe", decideUnsubscribeHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", mux); err != nil {
		log.Fatalf("Could not start server: %s\n", err)
	}
}