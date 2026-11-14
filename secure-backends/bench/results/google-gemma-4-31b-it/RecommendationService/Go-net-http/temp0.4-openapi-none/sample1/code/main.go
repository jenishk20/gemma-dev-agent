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
	);
	`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func recommenderHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		var p Product
		err := json.NewDecoder(r.Body).Decode(&p)
		if err != nil || p.Name == "" {
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

		err = tx.Commit()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method == http.MethodGet {
		tagsQuery := r.URL.Query().Get("tags")
		if tagsQuery == "" {
			http.Error(w, "Missing tags parameter", http.StatusBadRequest)
			return
		}

		tags := strings.Split(tagsQuery, ",")
		
		// Build query to find products matching any of the tags
		query := `SELECT DISTINCT p.name FROM products p JOIN tags t ON p.id = t.product_id WHERE t.tag IN (`
		placeholders := make([]string, len(tags))
		args := make([]interface{}, len(tags))
		for i, tag := range tags {
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
			var name string
			if err := rows.Scan(&name); err == nil {
				results = append(results, name)
			}
		}

		w.Header().Set("Content-Type", "text/html")
		var htmlOutput strings.Builder
		htmlOutput.WriteString("<html><body>")
		if len(results) == 0 {
			htmlOutput.WriteString("<p>No products found matching the tags.</p>")
		} else {
			htmlOutput.WriteString("<ul>")
			for _, name := range results {
				htmlOutput.WriteString(fmt.Sprintf("<li>%s</li>", html.EscapeString(name)))
			}
			htmlOutput.WriteString("</ul>")
		}
		htmlOutput.WriteString("</body></html>")
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