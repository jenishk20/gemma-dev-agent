require_relative "boot"

require "rails/all"

# The Rails Application Configuration
module MyForum
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Configure the app to use the secret provided in environment variables
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_fallback_secret_for_development_purposes_only" }

    # Ensure the app can serve HTML and JSON
    config.mime_enabled = true
  end
end