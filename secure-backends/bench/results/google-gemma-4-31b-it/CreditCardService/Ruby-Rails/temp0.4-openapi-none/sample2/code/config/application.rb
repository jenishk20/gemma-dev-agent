require_relative "boot"

require "rails/all"

# Require the rails process element
require "active_storage/engine"

Modules = "CreditCardService"

class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
  config.secret_key_base = ENV["APP_SECRET"] || "a_secure_fallback_secret_for_local_dev"
end