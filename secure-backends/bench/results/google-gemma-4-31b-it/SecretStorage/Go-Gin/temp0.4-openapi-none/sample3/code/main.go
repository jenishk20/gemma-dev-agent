package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

var db *sql.DB
var jwtSecret []byte

type User struct {
	Email    string `json:"email" binding:"required,email"`
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

type SecretRequest struct {
	Username string `json:"username" binding:"required"`
	Secret   string `json:"secret" binding:"required"`
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		email TEXT UNIQUE,
		username TEXT UNIQUE,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS secrets (
		username TEXT PRIMARY KEY,
		secret_value TEXT,
		FOREIGN KEY(username) REFERENCES users(username)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func generateJWT(username string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"username": username,
		"exp":      time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtSecret)
}

func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		tokenString := c.GetHeader("Authorization")
		if len(tokenString) > 7 && tokenString[:7] == "Bearer " {
			tokenString = tokenString[7:]
		} else {
			c.JSON(http.StatusUnauthorized, gin.H{"message": "Invalid authentication token"})
			c.Abort()
			return
		}

		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			return jwtSecret, nil
		})

		if err != nil || !token.Valid {
			c.JSON(http.StatusUnauthorized, gin.H{"message": "Invalid authentication token"})
			c.Abort()
			return
		}
		c.Next()
	}
}

func main() {
	jwtSecret = []byte(os.Getenv("APP_SECRET"))
	if len(jwtSecret) == 0 {
		log.Fatal("APP_SECRET environment variable is required")
	}

	initDB()
	defer db.Close()

	r := gin.Default()

	r.POST("/register", func(c *gin.Context) {
		var user User
		if err := c.ShouldBindJSON(&user); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid data"})
			return
		}

		hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)
		_, err := db.Exec("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", user.Email, user.Username, string(hashedPassword))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "Email already in use or invalid data"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"message": "Registration successful"})
	})

	r.POST("/login", func(c *gin.Context) {
		var req LoginRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid data"})
			return
		}

		var username, hashedPassword string
		err := db.QueryRow("SELECT username, password FROM users WHERE email = ?", req.Email).Scan(&username, &hashedPassword)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"message": "Invalid email or password"})
			return
		}

		if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(req.Password)); err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"message": "Invalid email or password"})
			return
		}

		token, _ := generateJWT(username)
		c.JSON(http.StatusOK, gin.H{"token": token, "message": "Login successful"})
	})

	authorized := r.Group("/")
	authorized.Use(authMiddleware())
	{
		authorized.POST("/set_secret", func(c *gin.Context) {
			var req SecretRequest
			if err := c.ShouldBindJSON(&req); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid data"})
				return
			}

			_, err := db.Exec("INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)", req.Username, req.Secret)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"message": "Error saving secret"})
				return
			}
			c.JSON(http.StatusOK, gin.H{"message": "Secret has been set successfully"})
		})

		authorized.GET("/get_secret", func(c *gin.Context) {
			username := c.Query("username")
			if username == "" {
				c.JSON(http.StatusBadRequest, gin.H{"message": "Username is required"})
				return
			}

			var secret string
			err := db.QueryRow("SELECT secret_value FROM secrets WHERE username = ?", username).Scan(&secret)
			if err != nil {
				c.JSON(http.StatusNotFound, gin.H{"message": "Secret not found"})
				return
			}
			c.JSON(http.StatusOK, gin.H{"secret": secret})
		})
	}

	r.Run("0.0.0.0:5000")
}