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

type Product map[string]string

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store the product name as a primary key and the rest of the 
	// unstructured properties as a JSON string in a 'properties' column.
	sqlStmt := `
	CREATE TABLE IF NOT EXISTS products (
		name TEXT PRIMARY KEY,
		properties TEXT
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatalf("Error creating table: %q: %s\n", err, sqlStmt)
	}
}

func handleAdd(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var prod Product
	if err := json.NewDecoder(r.Body).Decode(&prod); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	name, ok := prod["name"]
	if !ok || name == "" {
		http.Error(w, "Missing required field: name", http.StatusBadRequest)
		return
	}

	// Extract additional properties
	props := make(map[string]string)
	for k, v := range prod {
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

	// The schema asks for the "data" of the product. 
	// We return the full object (name + properties) as a JSON string inside the 'data' field.
	var props map[string]string
	json.Unmarshal([]byte(propsJSON), &props)
	
	fullProd := make(map[string]string)
	for k, v := range props {
		fullProd[k] = v
	}
	fullProd["name"] = name

	fullProdJSON, _ := json.Marshal(fullProd)
	
	response := map[string]string{"data": string(fullProdJSON)}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Name string `json:"name"`
		Data string `json:"data"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if req.Name == "" || req.Data == "" {
		http.Error(w, "Invalid upload query", http.StatusBadRequest)
		return
	}

	var prod Product
	if err := json.Unmarshal([]byte(req.Data), &prod); err != nil {
		http.Error(w, "Invalid data format", http.StatusBadRequest)
		return
	}

	// Ensure the name in the data matches the name provided in the request
	if prod["name"] != req.Name {
		http.Error(w, "Name mismatch", http.StatusBadRequest)
		return
	}

	props := make(map[string]string)
	for k, v := range prod {
		if k != "name" {
			props[k] = v
		}
	}

	propsJSON, _ := json.Marshal(props)
	_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", req.Name, string(propsJSON))
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

	rows, err := db.Query("SELECT name, properties FROM products")
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var results []Product
	searchLower := strings.ToLower(query)

	for rows.Next() {
		var name, propsJSON string
		if err := rows.Scan(&name, &propsJSON); err != nil {
			continue
		}

		var props map[string]string
		json.Unmarshal([]byte(propsJSON), &props)

		match := strings.Contains(strings.ToLower(name), searchLower)
		if !match {
			for k, v := range props {
				if strings.Contains(strings.ToLower(k), searchLower) || strings.Contains(strings.ToLower(v), searchLower) {
					match = true
					break
				}
			}
		}

		if match {
			p := make(Product)
			for k, v := range props {
				p[k] = v
			}
			p["name"] = name
			results = append(results, p)
		}
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

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}