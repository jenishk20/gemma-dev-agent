package main

import (
	"database/sql"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

type CartItem struct {
	ItemID int `json:"item_id"`
	Count  int `json:"count"`
}

type CreateCartResponse struct {
	CartID string `json:"cart_id"`
}

type AddToCartRequest struct {
	CartID string `json:"cart_id"`
	ItemID int    `json:"item_id"`
	Count  int    `json:"count"`
}

type RetrieveCartRequest struct {
	CartID string `json:"cart_id"`
}

type RetrieveCartResponse struct {
	Items []CartItem `json:"items"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS carts (
		id TEXT PRIMARY KEY
	);
	CREATE TABLE IF NOT EXISTS cart_items (
		cart_id TEXT,
		item_id INTEGER,
		count INTEGER,
		PRIMARY KEY (cart_id, item_id),
		FOREIGN KEY (cart_id) REFERENCES carts(id)
	);
	`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	app := fiber.New()

	app.Post("/create_cart", func(c *fiber.Ctx) error {
		cartID := uuid.New().String()
		_, err := db.Exec("INSERT INTO carts (id) VALUES (?)", cartID)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Could not create cart"})
		}
		return c.Status(201).JSON(CreateCartResponse{CartID: cartID})
	})

	app.Post("/add_to_cart", func(c *fiber.Ctx) error {
		req := new(AddToCartRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
		}

		if req.CartID == "" {
			return c.Status(400).JSON(fiber.Map{"error": "cart_id is required"})
		}

		var exists bool
		err := db.QueryRow("SELECT EXISTS(SELECT 1 FROM carts WHERE id = ?)", req.CartID).Scan(&exists)
		if err != nil || !exists {
			return c.Status(404).JSON(fiber.Map{"error": "Cart not found"})
		}

		// Use UPSERT logic for SQLite
		_, err = db.Exec(`
			INSERT INTO cart_items (cart_id, item_id, count) 
			VALUES (?, ?, ?) 
			ON CONFLICT(cart_id, item_id) 
			DO UPDATE SET count = count + excluded.count`, 
			req.CartID, req.ItemID, req.Count)
		
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		// Remove items with count <= 0
		db.Exec("DELETE FROM cart_items WHERE cart_id = ? AND count <= 0", req.CartID)

		return c.Status(200).SendString("Item added or removed successfully")
	})

	app.Post("/retrieve_cart", func(c *fiber.Ctx) error {
		req := new(RetrieveCartRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
		}

		var exists bool
		err := db.QueryRow("SELECT EXISTS(SELECT 1 FROM carts WHERE id = ?)", req.CartID).Scan(&exists)
		if err != nil || !exists {
			return c.Status(404).JSON(fiber.Map{"error": "Cart not found"})
		}

		rows, err := db.Query("SELECT item_id, count FROM cart_items WHERE cart_id = ?", req.CartID)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}
		defer rows.Close()

		items := []CartItem{}
		for rows.Next() {
			var item CartItem
			if err := rows.Scan(&item.ItemID, &item.Count); err != nil {
				continue
			}
			items = append(items, item)
		}

		return c.Status(200).JSON(RetrieveCartResponse{Items: items})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}