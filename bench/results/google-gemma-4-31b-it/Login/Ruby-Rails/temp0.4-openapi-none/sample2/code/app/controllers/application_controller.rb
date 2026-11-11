class ApplicationController < ActionController::API
  # Helper to generate a simple token based on APP_SECRET
  def generate_token(user)
    secret = ENV.fetch("APP_SECRET") { "development_secret_key_12345" }
    payload = { user_id: user.id, exp: Time.now.to_i + 3600 }
    # Simple Base64 encoded token for demonstration as per OpenAPI example
    Base64.strict_encode64("#{payload.to_json}.#{secret}")
  end
end