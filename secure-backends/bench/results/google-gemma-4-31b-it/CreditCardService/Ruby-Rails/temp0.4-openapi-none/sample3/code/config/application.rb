require_relative "boot"

require "rails/all"

# The Base class for all controllers in this application.
module CreditCardPhoneAssociationService
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app uses the secret from environment variable
    config.secret_key_base = ENV["APP_SECRET"] || "a_fallback_secret_for_development_12345"
  end
end