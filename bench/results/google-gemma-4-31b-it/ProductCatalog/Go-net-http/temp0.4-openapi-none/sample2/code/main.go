package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
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

	// We store the product name as a primary key and the unstructured properties as a JSON string
	sqlStmt := `
	CREATE TABLE IF NOT EXISTS products (
		name TEXT PRIMARY KEY,
		properties TEXT
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatalf("Database initialization failed: %s", err)
	}
}

func handleAdd(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var p Product
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	name, ok := p["name"]
	if !ok || name == "" {
		http.Error(w, "Missing required field: name", http.StatusBadRequest)
		return
	}

	// Separate name from properties
	props := make(map[string]string)
	for k, v := range p {
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
		http.Error(w, "Missing required query parameter: name", http.StatusBadRequest)
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

	// The schema asks for a response object with a 'data' field containing the product data
	// Since the product data is the set of properties, we return the JSON string of properties as the 'data' value
	response := map[string]string{"data": propsJSON}
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
		http.Error(w, "Invalid upload query", http.StatusBadRequest)
		return
	}

	if req.Name == "" || req.Data == "" {
		http.Error(w, "Invalid upload query", http.StatusBadRequest)
		return
	}

	// Validate that Data is valid JSON (as it must be in the format returned by /download)
	var dummy map[string]string
	if err := json.Unmarshal([]byte(req.Data), &dummy); err != nil {
		http.Error(w, "Invalid data format", http.StatusBadRequest)
		return
	}

	_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", req.Name, req.Data)
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
		http.Error(w, "Missing required query parameter: query", http.StatusBadRequest)
		return
	}

	// Search in name or in the properties JSON string
	rows, err := db.Query("SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?", "%"+query+"%", "%"+query+"%")
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

		product := Product{"name": name}
		for k, v := range props {
			product[k] = v
		}
		results = append(results, product)
	}

	response := map[string]interface{}{"results": results}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
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