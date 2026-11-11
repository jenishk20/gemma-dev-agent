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

	if r.Method == http.MethodGet {
		tagsParam := r.URL.Query().Get("tags")
		if tagsParam == "" {
			http.Error(w, "tags parameter is required", http.StatusBadRequest)
			return
		}

		searchTags := strings.Split(tagsParam, ",")
		query := `SELECT DISTINCT p.name FROM products p JOIN tags t ON p.id = t.product_id WHERE t.tag = ?`
		
		// For multiple tags, we build the query dynamically
		var finalQuery string
		var args []interface{}
		if len(searchTags) > 1 {
			var clauses []string
			for _, t := range searchTags {
				clauses = append(clauses, "t.tag = ?")
				args = append(args, t)
			}
			finalQuery = fmt.Sprintf("SELECT DISTINCT p.name FROM products p JOIN tags t ON p.id = t.product_id WHERE %s", strings.Join(clauses, " OR "))
		} else {
			finalQuery = query
			args = append(args, searchTags[0])
		}

		rows, err := db.Query(finalQuery, args...)
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
		var htmlOutput strings.Builder
		htmlOutput.WriteString("<html><body><ul>")
		for _, p := range products {
			htmlOutput.WriteString(fmt.Sprintf("<li>%s</li>", html.EscapeString(p)))
		}
		htmlOutput.WriteString("</ul></body></html>")
		w.Write([]byte(htmlOutput.String()))
		return
	}

	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func main() {
	initDB()
	defer db.Close()

	http.HandleFunc("/recommender", recommenderHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}