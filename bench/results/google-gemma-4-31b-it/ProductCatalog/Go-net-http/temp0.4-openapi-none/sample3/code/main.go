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
	Name string            `json:"name"`
	Data map[string]string `json:"-"` // Internal representation
}

// Custom MarshalJSON to flatten the map into the product object
func (p Product) MarshalJSON() ([]byte, error) {
	type Alias Product
	out := make(map[string]interface{})
	out["name"] = p.Name
	for k, v := range p.Data {
		out[k] = v
	}
	return json.Marshal(out)
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store unstructured properties as a JSON string in a single column
	sqlStmt := `CREATE TABLE IF NOT EXISTS products (name TEXT PRIMARY KEY, properties TEXT);`
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

	// Separate name from additional properties
	props := make(map[string]string)
	for k, v := range input {
		if k != "name" {
			props[k] = v
		}
	}

	propsJSON, _ := json.Marshal(props)
	_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
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

	// The schema asks for a response object with a 'data' field containing the product data
	// Since the input for /add was a JSON object, we return the serialized properties (including name)
	var props map[string]string
	json.Unmarshal([]byte(propsJSON), &props)
	props["name"] = name

	dataBytes, _ := json.Marshal(props)
	response := map[string]string{"data": string(dataBytes)}
	
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

	// Validate that Data is valid JSON and extract properties
	var props map[string]string
	if err := json.Unmarshal([]byte(input.Data), &props); err != nil {
		http.Error(w, "Invalid data format", http.StatusBadRequest)
		return
	}

	// Remove name from properties to avoid duplication in the JSON column
	delete(props, "name")
	propsJSON, _ := json.Marshal(props)

	_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", input.Name, string(propsJSON))
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

	// Search in name OR within the JSON properties string
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
		results = append(results, Product{Name: name, Data: props})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"results": results})
}

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/add", handleAdd)
	mux.HandleFunc("/download", handleDownload)
	mux.HandleFunc("/upload", handleUpload)
	mux.HandleFunc("/search", handleSearch)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}