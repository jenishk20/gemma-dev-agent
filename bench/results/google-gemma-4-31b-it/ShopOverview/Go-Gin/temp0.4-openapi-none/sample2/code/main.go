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
	MerchantEmail string `json:"merchant_email"`
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
		log.Fatal(err)
	}
}

func createJWT(merchantID int) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"merchant_id": merchantID,
		"exp":         time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtKey)
}

func validateJWT(tokenStr string) (int, error) {
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return jwtKey, nil
	})
	if err != nil || !token.Valid {
		return 0, fmt.Errorf("invalid token")
	}
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return 0, fmt.Errorf("invalid claims")
	}
	return int(claims["merchant_id"].(float64)), nil
}

func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		cookie, err := c.Cookie("AUTH_COOKIE")
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
			return
		}
		id, err := validateJWT(cookie)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
			return
		}
		c.Set("merchant_id", id)
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

	r := gin.Default()

	r.POST("/merchants/register", func(c *gin.Context) {
		var m Merchant
		if err := c.ShouldBindJSON(&m); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}
		hashedPw, _ := bcrypt.GenerateFromPassword([]byte(m.Password), bcrypt.DefaultCost)
		_, err := db.Exec("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", m.Email, m.Name, string(hashedPw))
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

		var m Merchant
		err := db.QueryRow("SELECT id, password FROM merchants WHERE email = ?", login.Email).Scan(&m.ID, &m.Password)
		if err != nil || bcrypt.CompareHashAndPassword([]byte(m.Password), []byte(login.Password)) != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
			return
		}

		token, _ := createJWT(m.ID)
		c.SetCookie("AUTH_COOKIE", token, 86400, "/", "", false, true)
		c.JSON(http.StatusOK, "Login successful")
	})

	authorized := r.Group("/")
	authorized.Use(authMiddleware())
	{
		authorized.POST("/merchants/upload-wares", func(c *gin.Context) {
			var body struct {
				CSV string `json:"csv"`
			}
			if err := c.ShouldBindJSON(&body); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
				return
			}

			reader := csv.NewReader(strings.NewReader(body.CSV))
			records, err := reader.ReadAll()
			if err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid CSV format"})
				return
			}

			merchantID := c.MustGet("merchant_id").(int)
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

			query := "SELECT w.name, w.price, w.description, m.email FROM wares w JOIN merchants m ON w.merchant_id = m.id WHERE 1=1"
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

			var wares []Ware
			for rows.Next() {
				var w Ware
				if err := rows.Scan(&w.Name, &w.Price, &w.Description, &w.MerchantEmail); err == nil {
					wares = append(wares, w)
				}
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