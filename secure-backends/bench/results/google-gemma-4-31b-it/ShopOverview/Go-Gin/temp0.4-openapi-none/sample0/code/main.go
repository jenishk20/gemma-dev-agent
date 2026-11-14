package main

import (
	"database/sql"
	"encoding/csv"
	"fmt"
	"html/template"
	"log"
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
	Email    string `json:"email" binding:"required,email"`
	Name     string `json:"name" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

type UploadRequest struct {
	CSV string `json:"csv" binding:"required"`
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS merchants (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		email TEXT UNIQUE,
		name TEXT,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS wares (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		merchant_id INTEGER,
		name TEXT,
		description TEXT,
		price REAL,
		FOREIGN KEY(merchant_id) REFERENCES merchants(id)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatalf("%q: %s\n", err, sqlStmt)
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
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
			return
		}
		email, err := validateToken(cookie)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
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
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
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
		var lr LoginRequest
		if err := c.ShouldBindJSON(&lr); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		var id int
		var hashedPassword string
		err := db.QueryRow("SELECT id, password FROM merchants WHERE email = ?", lr.Email).Scan(&id, &hashedPassword)
		if err != nil || bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(lr.Password)) != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
			return
		}
		token, _ := generateToken(lr.Email)
		c.SetCookie("AUTH_COOKIE", token, 3600*24, "/", "", false, true)
		c.JSON(http.StatusOK, "Login successful")
	})

	authorized := r.Group("/")
	authorized.Use(authMiddleware())
	{
		authorized.POST("/merchants/upload-wares", func(c *gin.Context) {
			var ur UploadRequest
			if err := c.ShouldBindJSON(&ur); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}
			email := c.MustGet("user_email").(string)
			var merchantID int
			db.QueryRow("SELECT id FROM merchants WHERE email = ?", email).Scan(&merchantID)

			reader := csv.NewReader(strings.NewReader(ur.CSV))
			records, err := reader.ReadAll()
			if err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid CSV format"})
				return
			}

			tx, _ := db.Begin()
			for _, record := range records {
				if len(record) < 3 {
					tx.Rollback()
					c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid CSV row"})
					return
				}
				price, err := strconv.ParseFloat(record[2], 64)
				if err != nil {
					tx.Rollback()
					c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid price format"})
					return
				}
				_, err = tx.Exec("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)", merchantID, record[0], record[1], price)
				if err != nil {
					tx.Rollback()
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
					return
				}
			}
			tx.Commit()
			c.Status(http.StatusOK)
		})

		authorized.GET("/wares", func(c *gin.Context) {
			minPriceStr := c.Query("minPrice")
			maxPriceStr := c.Query("maxPrice")

			query := `SELECT w.name, w.price, w.description, m.email 
					  FROM wares w JOIN merchants m ON w.merchant_id = m.id 
					  WHERE 1=1`
			var args []interface{}

			if minPriceStr != "" {
				min, err := strconv.ParseFloat(minPriceStr, 64)
				if err == nil {
					query += " AND w.price >= ?"
					args = append(args, min)
				}
			}
			if maxPriceStr != "" {
				max, err := strconv.ParseFloat(maxPriceStr, 64)
				if err == nil {
					query += " AND w.price <= ?"
					args = append(args, max)
				}
			}

			rows, err := db.Query(query, args...)
			if err != nil {
				c.String(http.StatusInternalServerError, "Database error")
				return
			}
			defer rows.Close()

			type WareRow struct {
				Name        string
				Price       float64
				Description string
				Email       string
			}
			var wares []WareRow
			for rows.Next() {
				var wr WareRow
				rows.Scan(&wr.Name, &wr.Price, &wr.Description, &wr.Email)
				wares = append(wares, wr)
			}

			tmpl := `<html><body><table border="1">
				<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>
				{{range .}}<tr><td>{{.Name}}</td><td>{{.Price}}</td><td>{{.Description}}</td><td>{{.Email}}</td></tr>{{end}}
				</table></body></html>`
			t, _ := template.New("wares").Parse(tmpl)
			c.Header("Content-Type", "text/html")
			t.Execute(c.Writer, wares)
		})
	}

	r.Run("0.0.0.0:5000")
}