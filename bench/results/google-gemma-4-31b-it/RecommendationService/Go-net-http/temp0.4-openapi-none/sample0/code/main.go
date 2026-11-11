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
	ID   int    `json:"id"`
	Name string `json:"product_name"`
	Tags []string `json:"tags"`
}

type ProductRequest struct {
	ProductName string   `json:"product_name"`
	Tags        []string `json:"tags"`
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
		name TEXT
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

func handleRecommender(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		tagsQuery := r.URL.Query().Get("tags")
		if tagsQuery == "" {
			http.Error(w, "Missing tags parameter", http.StatusBadRequest)
			return
		}

		searchTags := strings.Split(tagsQuery, ",")
		
		// Query to find products that have at least one of the tags
		query := `SELECT DISTINCT p.id, p.name FROM products p 
		          JOIN tags t ON p.id = t.product_id 
		          WHERE t.tag IN (`
		
		placeholders := make([]string, len(searchTags))
		args := make([]interface{}, len(searchTags))
		for i, tag := range searchTags {
			placeholders[i] = "?"
			args[i] = strings.TrimSpace(tag)
		}
		query += strings.Join(placeholders, ",") + ")"

		rows, err := db.Query(query, args...)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var results []string
		for rows.Next() {
			var id int
			var name string
			if err := rows.Scan(&id, &name); err != nil {
				continue
			}
			results = append(results, fmt.Sprintf("<li>%s (ID: %d)</li>", html.EscapeString(name), id))
		}

		w.Header().Set("Content-Type", "text/html")
		if len(results) == 0 {
			fmt.Fprint(w, "<ul><li>No products found matching the tags.</li></ul>")
		} else {
			fmt.Fprintf(w, "<ul>%s</ul>", strings.Join(results, ""))
		}
		return
	}

	if r.Method == http.MethodPost {
		var req ProductRequest
		decoder := json.NewDecoder(r.Body)
		if err := decoder.Decode(&req); err != nil {
			http.Error(w, "Invalid input", http.StatusBadRequest)
			return
		}

		if req.ProductName == "" || len(req.Tags) == 0 {
			http.Error(w, "Invalid input: product_name and tags are required", http.StatusBadRequest)
			return
		}

		tx, err := db.Begin()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", req.ProductName)
		if err != nil {
			tx.Rollback()
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		productID, _ := res.LastInsertId()
		for _, tag := range req.Tags {
			_, err = tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", productID, strings.TrimSpace(tag))
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
		fmt.Fprint(w, "Successful operation")
		return
	}

	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/recommender", handleRecommender)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}