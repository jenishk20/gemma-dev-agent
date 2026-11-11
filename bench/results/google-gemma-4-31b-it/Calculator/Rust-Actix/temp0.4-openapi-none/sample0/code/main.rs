use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct CalcRequest {
    expression: String,
}

#[derive(Serialize)]
struct CalcResponse {
    result: String,
}

/// A simple recursive descent parser for arithmetic expressions.
/// Supports +, -, *, / and parentheses.
struct Parser<'a> {
    tokens: std::str::SplitWhitespace<'a>,
    current: Option<String>,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        // Add spaces around operators to make splitting easier
        let formatted = input
            .replace('+', " + ")
            .replace('-', " - ")
            .replace('*', " * ")
            .replace('/', " / ")
            .replace('(', " ( ")
            .replace(')', " ) ");
        
        // We need to own the formatted string for the lifetime of the parser
        // but since we are in a request handler, we can just use a local string.
        // To keep it simple and compatible with the provided constraints, 
        // we will use a different approach for tokenization.
        Self {
            tokens: formatted.split_whitespace(),
            current: None,
        }
    }

    fn next_token(&mut self) {
        self.current = self.tokens.next().map(|s| s.to_string());
    }

    fn parse_expression(&mut self) -> Result<f64, String> {
        let mut left = self.parse_term()?;
        self.next_token();
        while let Some(ref token) = self.current {
            if token == "+" {
                self.next_token();
                left += self.parse_term()?;
            } else if token == "-" {
                self.next_token();
                left -= self.parse_term()?;
            } else {
                break;
            }
            self.next_token();
        }
        Ok(left)
    }

    fn parse_term(&mut self) -> Result<f64, String> {
        let mut left = self.parse_factor()?;
        self.next_token();
        while let Some(ref token) = self.current {
            if token == "*" {
                self.next_token();
                left *= self.parse_factor()?;
            } else if token == "/" {
                self.next_token();
                let right = self.parse_factor()?;
                if right == 0.0 { return Err("Division by zero".to_string()); }
                left /= right;
            } else {
                break;
            }
            self.next_token();
        }
        Ok(left)
    }

    fn parse_factor(&mut self) -> Result<f64, String> {
        self.next_token();
        let token = self.current.clone().ok_or("Unexpected end of expression")?;
        if token == "(" {
            let res = self.parse_expression()?;
            self.next_token();
            if self.current.as_deref() != Some(")") {
                return Err("Expected ')'".to_string());
            }
            Ok(res)
        } else {
            token.parse::<f64>().map_err(|_| format!("Invalid number: {}", token))
        }
    }
}

#[post("/calculator")]
async fn calculate(req: web::Json<CalcRequest>) -> impl Responder {
    // Basic tokenization by adding spaces around operators
    let formatted = req.expression
        .replace('+', " + ")
        .replace('-', " - ")
        .replace('*', " * ")
        .replace('/', " / ")
        .replace('(', " ( ")
        .replace(')', " ) ");

    let mut parser = Parser::new(&formatted);
    // The Parser::new logic above is slightly flawed because formatted is local.
    // Let's implement a simpler token-based approach inside the handler.
    
    // Re-implementing the logic to avoid lifetime issues with the formatted string
    let tokens: Vec<String> = formatted
        .split_whitespace()
        .map(|s| s.to_string())
        .collect();
    
    let mut pos = 0;

    fn parse_expr(tokens: &[String], pos: &mut usize) -> Result<f64, String> {
        let mut left = parse_term(tokens, pos)?;
        while *pos < tokens.len() {
            let token = &tokens[*pos];
            if token == "+" {
                *pos += 1;
                left += parse_term(tokens, pos)?;
            } else if token == "-" {
                *pos += 1;
                left -= parse_term(tokens, pos)?;
            } else {
                break;
            }
            *pos += 1; // This is a bit redundant with the logic but ensures movement
        }
        Ok(left)
    }

    // To avoid complex recursive closures in Rust, we use a helper struct or functions
    // Since we need to keep it in one file and simple, let's use a manual stack-based 
    // or simple recursive approach with a shared index.
    
    struct Eval<'a> {
        tokens: &'a [String],
        pos: usize,
    }

    impl<'a> Eval<'a> {
        fn parse_expression(&mut self) -> Result<f64, String> {
            let mut left = self.parse_term()?;
            while self.pos < self.tokens.len() {
                let op = &self.tokens[self.pos];
                if op == "+" {
                    self.pos += 1;
                    left += self.parse_term()?;
                } else if op == "-" {
                    self.pos += 1;
                    left -= self.parse_term()?;
                } else {
                    break;
                }
            }
            Ok(left)
        }

        fn parse_term(&mut self) -> Result<f64, String> {
            let mut left = self.parse_factor()?;
            while self.pos < self.tokens.len() {
                let op = &self.tokens[self.pos];
                if op == "*" {
                    self.pos += 1;
                    left *= self.parse_factor()?;
                } else if op == "/" {
                    self.pos += 1;
                    let right = self.parse_factor()?;
                    if right == 0.0 { return Err("DivByZero".to_string()); }
                    left /= right;
                } else {
                    break;
                }
            }
            Ok(left)
        }

        fn parse_factor(&mut self) -> Result<f64, String> {
            if self.pos >= self.tokens.len() {
                return Err("Unexpected end".to_string());
            }
            let token = &self.tokens[self.pos];
            self.pos += 1;
            if token == "(" {
                let res = self.parse_expression()?;
                if self.pos >= self.tokens.len() || &self.tokens[self.pos] != ")" {
                    return Err("Missing )".to_string());
                }
                self.pos += 1;
                Ok(res)
            } else {
                token.parse::<f64>().map_err(|_| "Invalid number".to_string())
            }
        }
    }

    let mut eval = Eval { tokens: &tokens, pos: 0 };
    match eval.parse_expression() {
        Ok(res) => {
            // Format result to remove trailing .0 if it's an integer
            let res_str = if res.fract() == 0.0 {
                format!("{:.0}", res)
            } else {
                res.to_string()
            };
            HttpResponse::Ok().json(CalcResponse { result: res_str })
        }
        Err(_) => HttpResponse::BadRequest().body("Invalid input"),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(calculate)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}