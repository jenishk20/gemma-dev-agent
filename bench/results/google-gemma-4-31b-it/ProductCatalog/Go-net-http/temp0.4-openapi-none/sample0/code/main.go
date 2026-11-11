package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	Name       string            `json:"name"`
	Properties map[string]string `json:"-"`
}

// MarshalJSON handles the "additionalProperties" requirement by flattening the map into the struct
func (p Product) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["name"] = p.Name
	for k, v := range p.Properties {
		m[k] = v
	}
	return json.Marshal(m)
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// Table to store product name and a JSON string of its unstructured properties
	sqlStmt := `
	CREATE TABLE IF NOT EXISTS products (
		name TEXT PRIMARY KEY,
		properties TEXT
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func handleAdd(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var input map[string]string
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	name, ok := input["name"]
	if !ok || name == "" {
		http.Error(w, "Missing required field: name", http.StatusBadRequest)
		return
	}

	// Extract additional properties (everything except name)
	props := make(map[string]string)
	for k, v := range input {
		if k != "name" {
			props[k] = v
		}
	}

	propsJSON, err := json.Marshal(props)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	_, err = db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func handleDownload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	name := r.URL.Query().Get("name")
	if name == "" {
		http.Error(w, "Missing required parameter: name", http.StatusBadRequest)
		return
	}

	var propsJSON string
	err := db.QueryRow("SELECT properties FROM products WHERE name = ?", name).Scan(&propsJSON)
	if err == sql.ErrNoRows {
		http.Error(w, "Product not found", http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	response := map[string]string{"data": propsJSON}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var input struct {
		Name string `json:"name"`
		Data string `json:"data"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, "Invalid upload query", http.StatusBadRequest)
		return
	}

	if input.Name == "" || input.Data == "" {
		http.Error(w, "Invalid upload query", http.StatusBadRequest)
		return
	}

	// Validate that Data is valid JSON (as it was produced by /download)
	var check map[string]string
	if err := json.Unmarshal([]byte(input.Data), &check); err != nil {
		http.Error(w, "Invalid data format", http.StatusBadRequest)
		return
	}

	_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", input.Name, input.Data)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func handleSearch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	query := r.URL.Query().Get("query")
	if query == "" {
		http.Error(w, "Missing required parameter: query", http.StatusBadRequest)
		return
	}

	// Search in name OR in the JSON properties string
	searchTerm := "%" + query + "%"
	rows, err := db.Query("SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?", searchTerm, searchTerm)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var results []Product
	for rows.Next() {
		var name, propsJSON string
		if err := rows.Scan(&name, &propsJSON); err != nil {
			continue
		}

		var props map[string]string
		json.Unmarshal([]byte(propsJSON), &props)
		results = append(results, Product{Name: name, Properties: props})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"results": results})
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/add", handleAdd)
	http.HandleFunc("/download", handleDownload)
	http.HandleFunc("/upload", handleUpload)
	http.HandleFunc("/search", handleSearch)

	port := "5000"
	fmt.Printf("Server starting on 0.0.0.0:%s\n", port)
	if err := http.ListenAndServe("0.0.0.0:"+port, nil); err != nil {
		log.Fatal(err)
	}
}