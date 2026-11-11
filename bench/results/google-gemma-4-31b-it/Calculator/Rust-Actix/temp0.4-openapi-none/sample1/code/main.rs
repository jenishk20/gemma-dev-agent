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

/// A simple recursive descent parser for basic arithmetic expressions.
/// Supports +, -, *, / and parentheses.
struct Parser<'a> {
    tokens: Vec<char>,
    pos: usize,
    input: &'a str,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Parser {
            tokens: input.chars().filter(|c| !c.is_whitespace()).collect(),
            pos: 0,
            input,
        }
    }

    fn peek(&self) -> Option<char> {
        self.tokens.get(self.pos).copied()
    }

    fn consume(&mut self) -> Option<char> {
        let res = self.peek();
        if res.is_some() {
            self.pos += 1;
        }
        res
    }

    fn parse_expression(&mut self) -> Result<f64, String> {
        let mut left = self.parse_term()?;
        while let Some(op) = self.peek() {
            if op == '+' || op == '-' {
                self.consume();
                let right = self.parse_term()?;
                if op == '+' {
                    left += right;
                } else {
                    left -= right;
                }
            } else {
                break;
            }
        }
        Ok(left)
    }

    fn parse_term(&mut self) -> Result<f64, String> {
        let mut left = self.parse_factor()?;
        while let Some(op) = self.peek() {
            if op == '*' || op == '/' {
                self.consume();
                let right = self.parse_factor()?;
                if op == '*' {
                    left *= right;
                } else {
                    if right == 0.0 {
                        return Err("Division by zero".to_string());
                    }
                    left /= right;
                }
            } else {
                break;
            }
        }
        Ok(left)
    }

    fn parse_factor(&mut self) -> Result<f64, String> {
        match self.consume() {
            Some('(') => {
                let res = self.parse_expression()?;
                if self.consume() != Some(')') {
                    return Err("Expected closing parenthesis".to_string());
                }
                Ok(res)
            }
            Some(c) if c.is_digit(10) || c == '.' => {
                let mut s = String::new();
                s.push(c);
                while let Some(next) = self.peek() {
                    if next.is_digit(10) || next == '.' {
                        s.push(self.consume().unwrap());
                    } else {
                        break;
                    }
                }
                s.parse::<f64>().map_err(|_| "Invalid number".to_string())
            }
            _ => Err("Unexpected token".to_string()),
        }
    }

    fn evaluate(&mut self) -> Result<f64, String> {
        let res = self.parse_expression()?;
        if self.pos != self.tokens.len() {
            return Err("Unexpected trailing characters".to_string());
        }
        Ok(res)
    }
}

#[post("/calculator")]
async fn calculate(req: web::Json<CalcRequest>) -> impl Responder {
    let mut parser = Parser::new(&req.expression);
    match parser.evaluate() {
        Ok(val) => {
            // Format to remove trailing zeros if it's an integer
            let result_str = if val.fract() == 0.0 {
                format!("{:.0}", val)
            } else {
                val.to_string()
            };
            HttpResponse::Ok().json(CalcResponse { result: result_str })
        }
        Err(_) => HttpResponse::BadRequest().body("Invalid input"),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new().service(calculate)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}