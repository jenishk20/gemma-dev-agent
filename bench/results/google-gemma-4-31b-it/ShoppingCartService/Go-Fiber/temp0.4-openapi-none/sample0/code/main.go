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

type RetrieveCartRequest struct {
	CartID string `json:"cart_id"`
}

type AddToCartRequest struct {
	CartID string `json:"cart_id"`
	ItemID int    `json:"item_id"`
	Count  int    `json:"count"`
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
		cart_id TEXT PRIMARY KEY
	);
	CREATE TABLE IF NOT EXISTS cart_items (
		cart_id TEXT,
		item_id INTEGER,
		count INTEGER,
		PRIMARY KEY (cart_id, item_id),
		FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
	);`
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
		_, err := db.Exec("INSERT INTO carts (cart_id) VALUES (?)", cartID)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Could not create cart"})
		}
		return c.Status(201).JSON(fiber.Map{"cart_id": cartID})
	})

	app.Post("/add_to_cart", func(c *fiber.Ctx) error {
		req := new(AddToCartRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).SendString("Invalid request")
		}

		var exists int
		err := db.QueryRow("SELECT 1 FROM carts WHERE cart_id = ?", req.CartID).Scan(&exists)
		if err != nil {
			return c.Status(404).SendString("Cart not found")
		}

		var currentCount int
		err = db.QueryRow("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", req.CartID, req.ItemID).Scan(&currentCount)
		if err != nil {
			// Item doesn't exist in cart yet
			currentCount = 0
		}

		newCount := currentCount + req.Count
		if newCount <= 0 {
			_, err = db.Exec("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", req.CartID, req.ItemID)
		} else {
			_, err = db.Exec("INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) ON CONFLICT(cart_id, item_id) DO UPDATE SET count = ?", 
				req.CartID, req.ItemID, newCount, newCount)
		}

		if err != nil {
			return c.Status(500).SendString("Database error")
		}

		return c.Status(200).SendString("Item added or removed successfully")
	})

	app.Post("/retrieve_cart", func(c *fiber.Ctx) error {
		req := new(RetrieveCartRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).SendString("Invalid request")
		}

		var exists int
		err := db.QueryRow("SELECT 1 FROM carts WHERE cart_id = ?", req.CartID).Scan(&exists)
		if err != nil {
			return c.Status(404).SendString("Cart not found")
		}

		rows, err := db.Query("SELECT item_id, count FROM cart_items WHERE cart_id = ?", req.CartID)
		if err != nil {
			return c.Status(500).SendString("Database error")
		}
		defer rows.Close()

		var items []CartItem
		for rows.Next() {
			var item CartItem
			if err := rows.Scan(&item.ItemID, &item.Count); err != nil {
				return c.Status(500).SendString("Database error")
			}
			items = append(items, item)
		}

		return c.Status(200).JSON(fiber.Map{"items": items})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}