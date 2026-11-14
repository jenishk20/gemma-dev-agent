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

type Ware struct {
	Name        string
	Description string
	Price       float64
	MerchantEmail string
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		panic(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS merchants (
		email TEXT PRIMARY KEY,
		name TEXT,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS wares (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		merchant_email TEXT,
		name TEXT,
		description TEXT,
		price REAL,
		FOREIGN KEY(merchant_email) REFERENCES merchants(email)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		panic(err)
	}
}

func createJWT(email string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtKey)
}

func validateJWT(c *gin.Context) {
	cookie, err := c.Cookie("AUTH_COOKIE")
	if err != nil {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	token, err := jwt.Parse(cookie, func(token *jwt.Token) (interface{}, error) {
		return jwtKey, nil
	})

	if err != nil || !token.Valid {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	claims := token.Claims.(jwt.MapClaims)
	c.Set("user_email", claims["email"])
	c.Next()
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
			c.JSON(http.StatusBadRequest, gin.H{"error": "Merchant already exists or database error"})
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

		var hashedPassword string
		err := db.QueryRow("SELECT password FROM merchants WHERE email = ?", lr.Email).Scan(&hashedPassword)
		if err != nil || bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(lr.Password)) != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
			return
		}

		token, err := createJWT(lr.Email)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not create token"})
			return
		}

		c.SetCookie("AUTH_COOKIE", token, 3600*24, "/", "", false, true)
		c.JSON(http.StatusOK, "Login successful")
	})

	authorized := r.Group("/")
	authorized.Use(validateJWT)
	{
		authorized.POST("/merchants/upload-wares", func(c *gin.Context) {
			var ur UploadRequest
			if err := c.ShouldBindJSON(&ur); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}

			email := c.GetString("user_email")
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
					c.JSON(http.StatusBadRequest, gin.H{"error": "CSV must have name, description, price"})
					return
				}
				price, err := strconv.ParseFloat(record[2], 64)
				if err != nil {
					tx.Rollback()
					c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid price format"})
					return
				}
				_, err = tx.Exec("INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)", email, record[0], record[1], price)
				if err != nil {
					tx.Rollback()
					c.JSON(http.StatusInternalServerError, gin.H{"error": "DB Error"})
					return
				}
			}
			tx.Commit()
			c.Status(http.StatusOK)
		})

		authorized.GET("/wares", func(c *gin.Context) {
			minPriceStr := c.Query("minPrice")
			maxPriceStr := c.Query("maxPrice")

			query := "SELECT w.name, w.price, w.description, w.merchant_email FROM wares w"
			var args []interface{}

			if minPriceStr != "" {
				query += " WHERE w.price >= ?"
				args = append(args, minPriceStr)
			}

			if maxPriceStr != "" {
				if minPriceStr != "" {
					query += " AND w.price <= ?"
				} else {
					query += " WHERE w.price <= ?"
				}
				args = append(args, maxPriceStr)
			}

			rows, err := db.Query(query, args...)
			if err != nil {
				c.Status(http.StatusInternalServerError)
				return
			}
			defer rows.Close()

			var wares []Ware
			for rows.Next() {
				var w Ware
				rows.Scan(&w.Name, &w.Price, &w.Description, &w.MerchantEmail)
				wares = append(wares, w)
			}

			tmpl := `
			<html>
			<body>
				<table border="1">
					<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>
					{{range .}}
					<tr>
						<td>{{.Name}}</td>
						<td>{{.Price}}</td>
						<td>{{.Description}}</td>
						<td>{{.MerchantEmail}}</td>
					</tr>
					{{end}}
				</table>
			</body>
			</html>`
			t, _ := template.New("wares").Parse(tmpl)
			c.Header("Content-Type", "text/html")
			t.Execute(c.Writer, wares)
		})
	}

	r.Run("0.0.0.0:5000")
}