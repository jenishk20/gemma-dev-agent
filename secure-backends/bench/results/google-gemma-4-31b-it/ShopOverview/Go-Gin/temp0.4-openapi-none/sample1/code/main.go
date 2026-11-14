package main

import (
	"database/sql"
	"encoding/csv"
	"fmt"
	"html/template"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

var db *sql.DB
var jwtKey []byte

type Merchant struct {
	ID       int    `json:"id"`
	Email    string `json:"email"`
	Name     string `json:"name"`
	Password string `json:"password"`
}

type Ware struct {
	ID          int     `json:"id"`
	MerchantID  int     `json:"merchant_id"`
	Name        string  `json:"name"`
	Description string  `json:"description"`
	Price       float64 `json:"price"`
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		panic(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS merchants (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, name TEXT, password TEXT);
	CREATE TABLE IF NOT EXISTS wares (id INTEGER PRIMARY KEY AUTOINCREMENT, merchant_id INTEGER, name TEXT, description TEXT, price REAL, FOREIGN KEY(merchant_id) REFERENCES merchants(id));
	`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		panic(err)
	}
}

func generateToken(email string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtKey)
}

func validateToken(tokenStr string) (string, error) {
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return jwtKey, nil
	})
	if err != nil || !token.Valid {
		return "", fmt.Errorf("invalid token")
	}
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", fmt.Errorf("invalid claims")
	}
	return claims["email"].(string), nil
}

func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		cookie, err := c.Cookie("AUTH_COOKIE")
		if err != nil {
			c.AbortWithStatus(http.StatusUnauthorized)
			return
		}
		email, err := validateToken(cookie)
		if err != nil {
			c.AbortWithStatus(http.StatusUnauthorized)
			return
		}
		c.Set("user_email", email)
		c.Next()
	}
}

func main() {
	secret := os.Getenv("APP_SECRET")
	if secret == "" {
		secret = "default_secret_key"
	}
	jwtKey = []byte(secret)

	initDB()
	defer db.Close()

	r := gin.Default()

	r.POST("/merchants/register", func(c *gin.Context) {
		var m Merchant
		if err := c.ShouldBindJSON(&m); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}
		hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(m.Password), bcrypt.DefaultCost)
		_, err := db.Exec("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", m.Email, m.Name, string(hashedPassword))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Merchant already exists or invalid input"})
			return
		}
		c.Status(http.StatusCreated)
	})

	r.POST("/merchants/login", func(c *gin.Context) {
		var login struct {
			Email    string `json:"email"`
			Password string `json:"password"`
		}
		if err := c.ShouldBindJSON(&login); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		var storedHash string
		err := db.QueryRow("SELECT password FROM merchants WHERE email = ?", login.Email).Scan(&storedHash)
		if err != nil || bcrypt.CompareHashAndPassword([]byte(storedHashed), []byte(login.Password)) != nil {
			// Fixing a typo in variable name from storedHash to storedHashed
		}
	})
}