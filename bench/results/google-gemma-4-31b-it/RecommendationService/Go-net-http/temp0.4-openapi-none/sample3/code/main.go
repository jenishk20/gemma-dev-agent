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
		name TEXT
	);
	CREATE TABLE IF NOT EXISTS tags (
		product_id INTEGER,
		tag TEXT,
		FOREIGN KEY(product_id) REFERENCES products(id)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func handleRecommender(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		tagsQuery := r.URL.Query().Get("tags")
		if tagsQuery == "" {
			http.Error(w, "Missing tags parameter", http.StatusBadRequest)
			return
		}

		searchTags := strings.Split(tagsQuery, ",")
		
		// Build query to find products that have at least one of the tags
		query := `SELECT DISTINCT p.name FROM products p 
				  JOIN tags t ON p.id = t.product_id 
				  WHERE t.tag IN (`
		
		args := make([]interface{}, len(searchTags))
		placeholders := make([]string, len(searchTags))
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

		var products []string
		for rows.Next() {
			var name string
			if err := rows.Scan(&name); err == nil {
				products = append(products, name)
			}
		}

		w.Header().Set("Content-Type", "text/html")
		var sb strings.Builder
		sb.WriteString("<html><body>")
		sb.WriteString("<h1>Recommended Products</h1>")
		if len(products) == 0 {
			sb.WriteString("<p>No products found matching the tags.</p>")
		} else {
			sb.WriteString("<ul>")
			for _, p := range products {
				sb.WriteString(fmt.Sprintf("<li>%s</li>", html.EscapeString(p)))
			}
			sb.WriteString("</ul>")
		}
		sb.WriteString("</body></html>")
		fmt.Fprint(w, sb.String())

	case http.MethodPost:
		var prod Product
		err := json.NewDecoder(r.Body).Decode(&prod)
		if err != nil || prod.Name == "" {
			http.Error(w, "Invalid input", http.StatusBadRequest)
			return
		}

		tx, err := db.Begin()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", prod.Name)
		if err != nil {
			tx.Rollback()
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		id, _ := res.LastInsertId()
		for _, tag := range prod.Tags {
			_, err = tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", id, strings.TrimSpace(tag))
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

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/recommender", handleRecommender)

	log.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}