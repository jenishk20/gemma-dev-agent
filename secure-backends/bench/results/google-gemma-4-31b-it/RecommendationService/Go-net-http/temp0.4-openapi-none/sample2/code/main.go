package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html"
	"log"
	"net/http"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	Name string   `json:"product_name"`
	Tags []string `json:"tags"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS products (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL
	);
	CREATE TABLE IF NOT EXISTS tags (
		product_id INTEGER,
		tag TEXT,
		FOREIGN KEY(product_id) REFERENCES products(id)
	);
	`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func recommenderHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		handlePost(w, r)
		return
	}

	if r.Method == http.MethodGet {
		handleGet(w, r)
		return
	}

	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func handlePost(w http.ResponseWriter, r *http.Request) {
	var p Product
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if p.Name == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	tx, err := db.Begin()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", p.Name)
	if err != nil {
		tx.Rollback()
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	id, _ := res.LastInsertId()
	for _, tag := range p.Tags {
		_, err = tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", id, tag)
		if err != nil {
			tx.Rollback()
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
	}

	if err := tx.Commit(); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	return
}

func handleGet(w http.ResponseWriter, r *http.Request) {
	tagsQuery := r.URL.Query().Get("tags")
	if tagsQuery == "" {
		http.Error(w, "Missing tags parameter", http.StatusBadRequest)
		return
	}

	tags := strings.Split(tagsQuery, ",")
	
	// Build query to find products that match at least one tag
	query := `SELECT DISTINCT p.name FROM products p JOIN tags t ON p.id = t.product_id WHERE t.tag IN (`
	var placeholders []string
	var args []interface{}
	for _, tag := range tags {
		placeholders = append(placeholders, "?")
		args = append(args, tag)
	}
	query += strings.Join(placeholders, ",") + `)`

	rows, err := db.Query(query, args...)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var products []string
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			continue
		}
		products = append(products, name)
	}

	w.Header().Set("Content-Type", "text/html")
	if len(products) == 0 {
		fmt.Fprintf(w, "<ul><li>No products found matching the tags.</li></ul>")
		return
	}

	fmt.Fprintf(w, "<ul>")
	for _, name := range products {
		fmt.Fprintf(w, "<li>%s</li>", html.EscapeString(name))
	}
	fmt.Fprintf(w, "</ul>")
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/recommender", recommenderHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}