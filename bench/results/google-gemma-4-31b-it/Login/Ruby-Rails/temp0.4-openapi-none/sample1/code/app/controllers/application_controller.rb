class ApplicationController < ActionController::API
  # Helper to generate a simple token based on APP_SECRET
  def generate_token(user)
    secret = ENV['APP_SECRET'] || 'default_secret_key'
    payload = { user_id: user.id, exp: Time.now.to_i + 3600 }
    # Simple Base64 encoded string for demonstration as we are limited to standard lib
    # In a real app, we would use a JWT gem.
    Base64.strict_encode64("#{payload.to_json}.#{secret}")
  end
end